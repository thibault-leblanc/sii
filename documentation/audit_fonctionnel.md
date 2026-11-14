# 🔎 Audit fonctionnel — Plateforme SII (POC)

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Périmètre** | Repo `PLATEFORME` (commit `dc70a58` + modifications non commitées sur `iaac/`) |
| **Nature** | Audit **statique** (lecture du code, des configs et des spécifications PDF). Aucun accès aux machines : l'état réel des Pi n'est pas vérifié. |
| **Hors périmètre** | Sécurité (prévue dans un audit ultérieur), dossiers `old*`, `iaac/sav/`, `configurations/raps1/`, `configurations/conteneurs/opcua-srv/`, `tests/` |
| **Référentiel** | `specifications_fonctionnelles_rincage.pdf`, `recapitulatif_procede_api.pdf`, `IHM_SCADA_Specification.pdf`, `archi_plateforme.drawio` (pages « Logique » et « Physique »), readmes du repo, intentions d'architecture précisées par le porteur du projet (§1.1) |

Niveaux d'impact : 🔴 **Bloquant** (la fonction ne marche pas ou cassera) · 🟠 **Majeur** (fonctionne dans le cas nominal, échoue sur un cas courant) · 🟡 **Mineur** (incohérence, dette, confort).

---

## 1. Synthèse

**Ce qui est solide**
- Une architecture claire et fidèle au modèle en couches OT : terrain (Modbus, VLAN20), contrôle (automate), supervision (OPC-UA, VLAN30), administration (VLAN10).
- La séparation physique / logique (simulateur passif contre automate décisionnel) est propre et conforme aux spécifications.
- Le simulateur et l'automate sont **pilotés par configuration** (`config_simu.json`, `config_api.json`), ce qui est une bonne base pour en faire un banc de test générique.
- L'IaaC existe dès le départ, avec un modèle lisible (physique / logique / réseaux) et un outil de visualisation et d'édition sans dépendance.

**Ce qui empêche aujourd'hui d'atteindre les objectifs**
1. **La « source de données unique » n'est pas branchée sur la HA.** Les agents rsync répliquent des données, mais les services HA (compose, `config_api.json`, `config_simu.json`, images) ne sont **pas lus depuis l'arborescence synchronisée**. Chaque nœud garde sa copie locale, maintenue à la main (§3).
2. **La bascule HA vers pi32 ne fonctionne pas au premier failover** : le `docker compose up` lancé depuis le conteneur agent résout les chemins de volumes dans le mauvais espace de noms (§4, H1).
3. **Le procédé se bloque en vidange infinie** dès que le pH passe sous 5 : le simulateur ne régénère jamais le pH (§5, P1).
4. **L'IaaC est descriptive, pas prescriptive.** Les paramètres (IP, chemins, noms) sont dupliqués dans 6 ou 7 endroits qui divergent déjà, et le générateur de netplan produirait une configuration qui **couperait l'accès** à pi51 et ferait perdre leur route par défaut à pi31 et pi32 (§2).

**Recommandation principale** : faire de l'objectif « serveur de données et rsync par VLAN » le chantier structurant, en y intégrant un **plan d'administration (infra)** synchronisé qui porte les artefacts de déploiement. La HA s'appuiera dessus et l'IaaC le décrira (§3 et §8).

### 1.1 Architecture cible : deux clusters

Intention du porteur de projet :

| Cluster | Nœuds | Rôle |
|---|---|---|
| **Fonctionnel** | pi31, pi32 (pi3X) | Porte le métier : automates, simulations |
| **Infrastructure** | pi51 seul aujourd'hui, futurs pi5X | Porte les services de socle : **gestion unique de toutes les données de la plateforme**, gestionnaire de HA et de conteneurs, GIA (gestion des identités et des accès, rien d'existant à ce jour) plus tard… |
| **Supervision** (à terme) | À définir | SCADA dans **son propre VLAN**. Aujourd'hui, FUXA tourne sur le poste d'administration 192.168.10.49. |

La plateforme est appelée à grossir (autres procédés, automates, simulateurs : `sim-es-2`, `api2`, `api3` sur le schéma en donnent l'idée). Le modèle doit donc permettre d'ajouter un nœud, un cluster ou une instance **sans retoucher l'existant**.

C'est un découpage sain, qui correspond à la séparation classique **plan de contrôle / plan de données**. Il a quatre conséquences sur l'audit :

1. **L'implémentation actuelle ne le reflète pas encore.** Le gestionnaire de HA (`ha-cluster`) tourne *sur* les nœuds fonctionnels et prend ses décisions localement (keepalived). Il n'existe ni gestionnaire de conteneurs côté pi51, ni notion de cluster dans l'IaaC. Le `hote_parent: ["pi31","pi32"]` en cours de modification est un contournement : la ressource devrait cibler **un cluster**, pas une liste de nœuds (§2.2).
2. **Il faut répartir les rôles entre infra et nœuds** pour que la panne de pi51, encore seul, n'empêche pas les bascules : **pi51 définit l'état voulu** (quoi déployer, où, avec quelle config, publié dans `/srv/sii/infra`) et des **agents locaux sur les pi3X l'appliquent et détectent les pannes** (VRRP). Si pi51 tombe, le cluster fonctionnel continue de tourner et de basculer sur la dernière configuration reçue (§4, H10).
3. **La réplication des données doit anticiper le futur cluster infra** : chemins indépendants du nœud (`/srv/sii`), sources adressées par une IP de service ou une VIP plutôt que par l'IP de pi51, et un format d'état voulu indépendant de l'outil de transport (rsync aujourd'hui, autre chose demain) (§3.3).
4. **Le SCADA n'a pas encore de place dans l'infrastructure.** Il tourne en conteneur de dev sur le poste d'administration (192.168.10.49, bridge `:1881`) : la supervision traverse donc le pare-feu du VLAN10 vers le VLAN30 pour joindre l'automate. La cible est un cluster de supervision dans un VLAN dédié, à créer dans l'IaaC (nouveau VLAN, flux VLAN supervision → VLAN30:4840). Il faudra préciser le rôle respectif de ce nouveau VLAN et du VLAN30 actuel, déjà nommé « Supervision ».
5. **Toute donnée transite par le cluster infra** : on dépose dans le dossier du périmètre concerné sur pi5X, puis la synchronisation l'achemine vers le cluster cible. Il n'y a pas de dépôt direct sur un nœud fonctionnel ou de supervision. Le §3.3 en découle directement.

---

## 2. IaaC comme source de vérité

### 2.1 Écarts entre `infrastructure.json` et la réalité du repo

| # | Impact | Constat | Où |
|---|---|---|---|
| I1 | 🔴 | **pi51 n'a pas d'interface `eth0.10`** dans l'IaaC, alors que son netplan réel lui donne `192.168.10.12`. Le script de provisioning généré **supprimerait l'accès administration** de pi51. pi51 n'a pas non plus de `liaison_physique` vers le switch. | [infrastructure.json:198-218](../iaac/infrastructure.json#L198-L218) vs [99-pi51-netplan.yaml](../configurations/machines/pi51/99-pi51-netplan.yaml) |
| I2 | 🔴 | **Le générateur de netplan n'ajoute la route par défaut et les DNS que sur les interfaces non virtuelles.** Pour pi31 et pi32, l'IP est sur `eth0.10` (virtuelle) : le netplan généré n'aurait ni passerelle ni DNS, contrairement aux netplans réels. | [serveur.py:128-137](../iaac/serveur.py#L128-L137) |
| I3 | 🟠 | `schema.json` déclare `hote_parent` comme `string`, alors que la modification en cours le passe en liste pour `ha-cluster`. L'éditeur piloté par le schéma va mal se comporter. | [schema.json:71](../iaac/schema.json#L71) |
| I4 | 🟠 | `ha-cluster` : interface déclarée en `VLAN20`, alors que la VIP `192.168.10.251` et le heartbeat (`eth0.10`) sont sur le VLAN10. | [infrastructure.json:276-282](../iaac/infrastructure.json#L276-L282) |
| I5 | 🟠 | `fichier_configuration_central: donnees/vlan20/donnees/config_cluster.json`, mais l'agent HA lit `/config/config_cluster.json`, c'est-à-dire le **dossier parent** du compose, et non l'arborescence synchronisée. | [infrastructure.json:273](../iaac/infrastructure.json#L273), [cluster/docker-compose.yml](../configurations/conteneurs/cluster/docker-compose.yml) |
| I6 | 🟡 | Commutateur `port2` : IP `192.168.10.11`, identique à celle de pi32. Copie involontaire, ou port d'admin à documenter ? | [infrastructure.json:74-79](../iaac/infrastructure.json#L74-L79) |
| I7 | 🟡 | `depot_source` faux pour `ha-cluster`, `donnees-vlan-*` et `sync-vlan-*` : les dossiers réels sont `conteneurs/cluster`, `conteneurs/donnees/serveur` et `conteneurs/donnees/agent-sync`. | [infrastructure.json:270, 289, 305…](../iaac/infrastructure.json#L270) |
| I8 | 🟡 | `chemin_deploiement` (`vlan20`, `vlan20-sync`) ≠ dossiers réellement créés par les scripts (`donnees-vlan-20`, `sync-vlan-20`). | [deploiement_sync.sh](../configurations/conteneurs/donnees/agent-sync/deploiement_sync.sh) |
| I9 | 🟡 | `ip_gestion` est utilisé sur une interface (pi32 `eth0`) mais n'existe pas dans le schéma des interfaces. | [infrastructure.json:163](../iaac/infrastructure.json#L163) |

### 2.2 Ce que l'IaaC ne décrit pas (angles morts)

- **Le SCADA FUXA**, absent du modèle. Où tourne-t-il (PC de dev en bridge `:1881`, ou un Pi) ?
- **Les flux** : aucune matrice de flux (Modbus 20.20→20.10:502, OPC-UA →30.20:4840, SSH/rsync →10.10/10.11, VRRP sur VLAN10, FTP →20.30/30.30). Sur une plateforme OT, la matrice de flux est l'objet central pour les tests de briques (IDS, pare-feu, diode…) et pour générer la checklist pare-feu.
- **Les réseaux Docker macvlan** (parent, plage IPAM), alors qu'ils conditionnent tous les conteneurs.
- **Le stockage et la réplication** : partages, sens de synchronisation, cibles. C'est pourtant l'objectif prioritaire.
- **La configuration HA** : `config_cluster.json` duplique la VIP, les priorités et les services sans lien avec `infrastructure.json`.
- **Les clusters** (§1.1) : il manque une section `clusters` (membres, rôle, VIP, cluster d'appartenance). Une ressource logique déclarerait alors `cluster_cible: "fonctionnel"`, avec une préférence de placement et un groupe de bascule, au lieu d'un `hote_parent` qui énumère des nœuds. C'est aussi ce qui permettra d'ajouter un pi33 ou un pi52 sans toucher aux ressources.
- **Le poste d'administration** (192.168.10.49) qui héberge aujourd'hui le SCADA de dev, ainsi que le futur VLAN de supervision.
- *Les instances `sim-es-2`, `api2` et `api3` du schéma ne représentent qu'une perspective de croissance : inutile de les modéliser. En revanche, le modèle doit rendre leur ajout trivial (clusters, plages d'adresses par VLAN, contrat d'échange générique P9).*

### 2.3 Constat critique

Aujourd'hui, un même paramètre vit à plusieurs endroits. Par exemple, l'IP du FTP VLAN20 apparaît dans `infrastructure.json`, `commande.sh`, le `docker-compose.yml` généré, le readme et, implicitement, dans les plages IPAM. Les IP de pi31 et pi32 sont **en dur dans le Dockerfile** de l'agent de synchronisation. Rien ne garantit la cohérence : **l'IaaC documente, mais ne fait pas foi**. Pour qu'elle devienne la source de vérité, il faut **inverser le sens** : les fichiers de déploiement (compose, `.env`, `config_cluster.json`, commandes) doivent être **générés** depuis `infrastructure.json`, comme c'est déjà amorcé pour netplan.

### 2.4 Écarts entre le schéma draw.io et l'IaaC

Le schéma `archi_plateforme.drawio` constitue **une deuxième source de vérité**, maintenue à la main, et il diverge déjà de l'IaaC :

| # | Impact | Page | Constat |
|---|---|---|---|
| S1 | 🟠 | Physique | **Port 4 du switch** : le schéma le relie à **pi51**, l'IaaC à **pi32** (trunk). **pi32 n'apparaît pas** sur la page physique. |
| S2 | 🟠 | Physique | **Port 3 (pi31)** : le schéma indique un trunk `vl10 vl20`, alors que l'IaaC et le netplan de pi31 utilisent les VLANs **10, 20 et 30**. Sans le VLAN30, `api-rincage` ne peut pas exposer l'OPC-UA au SCADA. |
| S3 | 🟡 | Physique | **Port 1** est étiqueté `adm` sur le schéma, alors que l'IaaC déclare un `port2` en accès VLAN10 avec l'IP .11 (voir I6). Le **port 5 → `srv1`** (serveur générique) n'existe pas dans l'IaaC. |
| S4 | 🟡 | Logique | **`scada1` (192.168.30.10) est dessiné dans le cadre pi51.** Ce n'est ni la réalité (poste .49) ni la cible (cluster de supervision dans son propre VLAN, §1.1). À redessiner. |
| S5 | 🟡 | Logique | Le cadre « pi31 » contient tous les conteneurs fonctionnels, mais il n'y a ni cadre pi32, ni notion de cluster, ni VIP 192.168.10.251. Les flux de réplication (pi51 → pi3X) ne sont pas représentés. |
| S6 | 🟡 | Logique | Côté WAN : box .254, pare-feu .197 (✅ cohérent avec l'IaaC). Le **poste d'administration 192.168.10.49**, qui héberge FUXA, est dessiné côté box/WAN et absent de l'IaaC. Le flux FUXA (VLAN10) → automate (192.168.30.20:4840) traverse le pare-feu et n'est documenté nulle part. |
| S7 | ✅ | Logique | Adresses VLAN10 cohérentes : pi31 .10, pi32 .11, pi51 .12, switch .90, ainsi que les IP des conteneurs existants. |

**Recommandation** : désigner **`infrastructure.json` comme unique référence** et faire du rendu de topologie de l'interface IaaC la vue technique de référence, avec export possible. Le draw.io resterait pour les vues **conceptuelles** (clusters, plans de contrôle et de données, chaîne procédé, découpage interne des conteneurs), qui changent peu, et ne porterait plus d'adresses ni de numéros de port.

---

## 3. 🎯 Serveur de données et rsync par VLAN (objectif prioritaire)

### 3.1 Fonctionnement actuel

```text
[Équipements VLAN20] --FTP--> donnees-vlan-20 (192.168.20.30, pi51)
                                  │  /home/pi51/donnees/vlan20  (racine FTP)
                                  └─ /home/pi51/donnees/vlan20/donnees  (seul sous-dossier synchronisé)
                                              │ ro
                              sync-vlan-20 (macvlan 192.168.20.31)
                                  │ rsync/ssh toutes les 60 s, via la passerelle 192.168.20.1 (VLAN20→VLAN10)
                     ┌────────────┴────────────┐
       pi31:/home/pi31/donnees/vlan20/donnees   pi32:/home/pi32/donnees/vlan20/donnees
```
Même schéma pour le VLAN30.

### 3.2 Constats

| # | Impact | Constat |
|---|---|---|
| D1 | 🔴 | **Les données synchronisées ne sont consommées par personne.** Les services HA montent `./config_api.json`, `./config_simu.json` et leur compose depuis `~/api/rincage` et `~/simulation/rincage`, qui ne sont pas synchronisés. L'agent HA lit sa config dans `~/config_cluster.json` (I5). Résultat : il n'y a **pas de source unique** et les deux nœuds peuvent diverger silencieusement. |
| D2 | 🔴 | **Premier déploiement sur un nœud neuf** : rsync ne crée pas les répertoires parents. `/home/pi3x/donnees/vlan20/` doit déjà exister, or le provisioning ne crée que `/home/pi3x/donnees`. La synchro échoue tant que l'arborescence n'est pas créée à la main. |
| D3 | 🟠 | **Les deux cibles sont traitées en séquence et sans timeout.** Si pi31 est éteint (cas typique d'une HA), la connexion SSH vers pi31 bloque jusqu'au timeout TCP (environ 2 min) à **chaque cycle**, ce qui retarde d'autant la mise à jour de pi32, le nœud qui a justement repris la main. |
| D4 | 🟠 | **Le flux de réplication passe par les VLANs de procédé.** Les agents sont en macvlan VLAN20/30 et atteignent le VLAN10 via le pare-feu. Fonctionnellement, cela impose des règles inter-zones et une dépendance au pare-feu pour un flux qui relève de l'administration. Le cloisonnement par VLAN devrait porter sur **la source des données** (quel FTP), pas sur **le transport**. |
| D5 | 🟠 | **Pas de mise à jour atomique.** Un ensemble de fichiers cohérents (compose et config, ou nouvelle image `.tar` et config associée) peut être vu à moitié copié par l'agent HA. rsync n'a pas `--delay-updates`. |
| D6 | 🟠 | **Aucune observabilité.** On ne sait pas si la dernière synchro a réussi ni quand. Il n'y a ni horodatage, ni code retour exploité, ni healthcheck Docker. La HA ne peut pas savoir si sa config est fraîche. |
| D7 | 🟡 | La cible et les chemins sont **en dur dans le Dockerfile** (`pi31@192.168.10.10`, `/home/pi31/…`). Ajouter un nœud oblige à reconstruire l'image. Les chemins diffèrent par nœud (`/home/pi31` contre `/home/pi32`), ce qui complique tout le reste (HA, compose). |
| D8 | 🟠 | La racine FTP (`vlan20/`) ≠ le dossier synchronisé (`vlan20/donnees/`) : un dépôt à la racine FTP n'est jamais répliqué. Or la règle est que **toute donnée déposée sur pi5X est destinée à être synchronisée** (§1.1). Il faut donc aligner la racine FTP sur le dossier synchronisé, ou rendre explicite un sas `entrant/` → `donnees/`. Personne ne crée `donnees/` : Docker le créera en `root` au premier montage. |
| D9 | 🟡 | `-z` (compression) sur un LAN gigabit avec des Pi 3B coûte du CPU pour rien. |
| D10 | 🟡 | Le readme [donnees/readme.md](../configurations/conteneurs/donnees/readme.md) pointe vers `./serveur-ftp/`, alors que le dossier s'appelle `./serveur/`. Le `docker-compose.yml` commité dans `serveur/` est un artefact généré. |
| D11 | ❓ | Ancien conteneur de test `test-opcua-srv` (script [pi31/opcua-srv.sh](../configurations/machines/pi31/opcua-srv.sh)) : il utilisait **192.168.20.30 et 192.168.30.30**, les IP des FTP actuels. S'il tourne encore sur pi31, il y a un conflit d'IP. À vérifier sur la machine. |

### 3.3 Architecture cible proposée

Principe : **le cluster infra (pi51 aujourd'hui) est la source de vérité des fichiers. Les nœuds du cluster fonctionnel en sont des répliques en lecture seule, avec des chemins identiques sur tous les nœuds.** Le dossier `infra/` est le **canal par lequel le plan de contrôle (pi51) publie l'état voulu** vers le plan de données (pi3X).

```text
pi51:/srv/sii/                      (source, écrite par FTP et par l'admin)
├── infra/                          ← NOUVEAU : plan d'administration (VLAN10)
│   ├── services/
│   │   ├── api-rincage/   docker-compose.yml, config_api.json
│   │   └── sim-rincage/   docker-compose.yml, config_simu.json
│   ├── images/            *.tar (versionnées : api-rincage_1.2.0.tar)
│   └── cluster/           config_cluster.json
├── vlan20/donnees/                 (ingestion FTP terrain)
└── vlan30/donnees/                 (ingestion FTP supervision)

pi31:/srv/sii/  et  pi32:/srv/sii/  ← répliques identiques (mêmes chemins)
```

- **Règle de gestion** : chaque dossier de premier niveau de `/srv/sii` est un **périmètre**, déclaré dans l'IaaC avec sa source et son **cluster destinataire**. Ajouter des données pour un cluster revient à déposer dans son périmètre sur pi5X ; ajouter un cluster (supervision, futur procédé) revient à déclarer un périmètre, sans code à écrire.
- **Un agent par périmètre** (`infra`, `vlan20`, `vlan30`) : on garde votre logique de cloisonnement. Les sources sont distinctes et un agent ne voit que son dossier en `:ro`. Le **transport** se fait sur le VLAN10 (macvlan `eth0.10` ou `network_mode: host` sur pi51), sans traverser le pare-feu.
- **Cibles paramétrées** par variables d'environnement (`SYNC_SOURCE`, `SYNC_TARGETS="pi31@192.168.10.10 pi32@192.168.10.11"`, `SYNC_DEST=/srv/sii/vlan20/donnees`, `SYNC_INTERVAL`). L'image devient générique et les valeurs sont générées depuis l'IaaC.
- **rsync robuste** : `--mkpath` (D2), `-o ConnectTimeout=5` et cibles indépendantes (D3), `--delay-updates` (D5), sans `-z` (D9).
- **Statut publié** : après chaque cycle, écriture de `.sync_status.json` (horodatage, résultat par cible) dans la destination (D6). La HA et la supervision peuvent le lire.
- **Consommation par la HA** : les services HA sont lancés depuis `/srv/sii/infra/services/<svc>`, l'agent HA lit `/srv/sii/infra/cluster/config_cluster.json` et charge uniquement `/srv/sii/infra/images/*.tar`. Le montage se fait **au même chemin** dans l'agent HA (`/srv/sii:/srv/sii:ro`), ce qui corrige aussi H1.
- **Préparer le futur cluster infra** : les agents tournent sur le cluster infra et ciblent les nœuds listés dans l'IaaC (`clusters.fonctionnel.membres`), jamais des IP en dur. Le jour où un pi52 rejoindra pi51, il faudra répliquer la **source** elle-même (rsync primaire → secondaire en premier lieu, puis éventuellement un stockage répliqué). Les FTP, déjà adressés par une IP de conteneur (20.30, 30.30), pourront basculer sans que les équipements terrain changent de cible.
- **Hors périmètre de cette étape** : les données **produites** par les nœuds (logs, historiques) ne remontent pas vers pi51, car la réplication est unidirectionnelle. C'est à traiter plus tard (historian central sur pi51, ou flux inverse dédié).

### 3.4 Critères de recette proposés

1. Un fichier déposé en FTP sur `192.168.20.30` est présent sur pi31 **et** pi32 en moins de 70 s ; idem pour le VLAN30.
2. pi31 éteint : pi32 continue d'être synchronisé en moins de 70 s (pas de blocage par timeout).
3. Nœud fraîchement provisionné : la synchro fonctionne sans création manuelle de dossier.
4. Une modification de `infra/services/api-rincage/config_api.json` sur pi51 est visible sur les deux nœuds, et `.sync_status.json` est à jour.
5. Un fichier supprimé sur pi51 disparaît des répliques (`--delete`), sans jamais supprimer les données d'un autre VLAN.
6. Bascule pi31 → pi32 : pi32 démarre `api-rincage` **avec la config issue de `/srv/sii/infra`**.

---

## 4. Haute disponibilité (`ha-cluster`)

| # | Impact | Constat | Où |
|---|---|---|---|
| H1 | 🔴 | **Le repli `docker compose up` est cassé.** Il est lancé *dans* l'agent HA avec `cd /config/<svc>`. Compose transforme `./config_api.json` en `/config/api/rincage/config_api.json` et l'envoie au démon Docker **de l'hôte**, où ce chemin n'existe pas. Docker crée alors un *dossier* à la place du fichier et le conteneur ne démarre pas. Or ce repli est le chemin utilisé lors du **premier failover sur pi32** : le conteneur n'existe pas encore, donc `docker start` échoue. | [cluster/Dockerfile:63-67](../configurations/conteneurs/cluster/Dockerfile#L63-L67) |
| H2 | 🟠 | **Les bascules peuvent faire du ping-pong.** Sur incident de pi31 (priorité 100 - 20 = 80 < 90), pi32 devient maître. pi31 passe en BACKUP, ce qui crée `/tmp/force_backup`, et sa sonde redevient « OK ». Sa priorité remonte à 100 et, la préemption étant active par défaut, pi31 reprend la main… puis retombe si le défaut persiste. Il faut `nopreempt` ou une logique de retour manuel. | [cluster/Dockerfile:32-35, 52-56](../configurations/conteneurs/cluster/Dockerfile#L32) |
| H3 | 🟠 | **La sonde est trop permissive** : `grep -E "api-rincage\|sim-rincage"` réussit si **un seul** des deux services tourne. Un automate arrêté avec le simulateur actif est vu comme sain. | [cluster/Dockerfile:56](../configurations/conteneurs/cluster/Dockerfile#L56) |
| H4 | 🟠 | **Bascule « à froid »** : la mémoire de l'automate (défaut, mode vidange) et les valeurs OPC-UA (`EnMarche` revient à `False`) sont perdues. Le procédé s'arrête et un défaut actif est **implicitement acquitté**. C'est acceptable pour un POC, mais doit être documenté comme comportement attendu, ou traité (mémoire rémanente). | [app.py](../configurations/conteneurs/api/rincage/app.py) |
| H5 | 🟠 | **Un seul groupe de bascule pour tout.** Un unique VRRP (`COEUR_SII`) fait basculer *tous* les services ensemble. Or le simulateur représente *l'usine physique* : le faire basculer avec l'automate revient à « réinitialiser l'usine » (niveau, pH, pièces) à chaque panne d'automate, ce qui fausse tout scénario de test de redondance. Recommandation : garder le simulateur dans le cluster fonctionnel (§1.1), mais dans des **groupes de bascule distincts** (simulation / automate / SCADA), chacun avec son instance VRRP (VRID) et ses priorités. On pourra alors tester « l'automate bascule, l'usine continue ». | [config_cluster.json](../configurations/conteneurs/cluster/config_cluster.json) |
| H6 | 🟠 | **Risque de double maître (split-brain)** : le heartbeat passe par le VLAN10. Si le VLAN10 est coupé mais pas les VLANs 20/30, les deux nœuds deviennent maîtres et démarrent `api-rincage` avec **les mêmes IP macvlan**, ce qui crée un conflit ARP sur le terrain. Prévoir une deuxième voie de heartbeat ou un contrôle avant démarrage (ping de l'IP de service). | — |
| H7 | 🟡 | La priorité n'est lue que dans l'entrée `api-rincage` ; elle est dupliquée par service sans être utilisée. Il vaut mieux la porter au niveau du nœud. | [cluster/Dockerfile](../configurations/conteneurs/cluster/Dockerfile) |
| H8 | 🟡 | L'auto-loader scanne **tout** `/config` (tout le home) à la recherche de `.tar`, y compris les `.tar.old`, sauvegardes et données FTP. Il faut le restreindre à un dossier d'images. Le script [chargeur_intelligent.sh](../configurations/machines/pi31/chargeur_intelligent.sh) (chemins `/home/pi/…`) et `check_api.sh`/`check_sim.sh` sont obsolètes. | — |
| H10 | 🟠 | **Rôle du gestionnaire HA par rapport à la cible (§1.1).** Le gestionnaire de HA et de conteneurs doit appartenir au cluster infra, mais il est aujourd'hui entièrement sur les nœuds fonctionnels, et sa config vient du disque local. Le centraliser *entièrement* sur pi51 (seul nœud) ferait de pi51 un point unique de défaillance pour les bascules. Cible recommandée, en deux niveaux : **gestionnaire sur pi51** (génère l'état voulu depuis l'IaaC, le publie dans `/srv/sii/infra`, collecte l'état réel des nœuds) et **agent sur chaque pi3X** (applique l'état voulu, détecte les pannes en VRRP, bascule de façon autonome). Remarque : les orchestrateurs du marché (Swarm, K3s, Nomad) gèrent mal le **macvlan avec IP fixes** indispensable en OT, et K3s est lourd pour un Pi 3B (1 Go). Un agent maison est donc justifié pour ce POC, à condition d'avoir cette séparation claire. | — |
| H9 | 🟡 | La plage IPAM macvlan `.16/28` (.16–.31) contient les IP statiques `.20`, `.30` et `.31`, et elle est identique sur tous les hôtes. Il n'y a pas de conflit tant que tout est statique, mais c'est fragile. Il vaut mieux déclarer la plage dans l'IaaC et la placer hors des statiques. | [creation_vlan.sh](../configurations/machines/pi31/creation_vlan.sh) |

---

## 5. Chaîne procédé (simulateur ↔ automate ↔ SCADA) par rapport aux spécifications

### 5.1 Cohérence des échanges
- **Modbus simulateur ↔ automate** : ✅ cohérent (coils 0–4, DI 10–12, IR 20–21, échelles ×10 et ×100).
- **OPC-UA automate ↔ FUXA** : ✅ les 16 tags du device `OPCUA_RINCAGE` (`opc.tcp://192.168.30.20:4840`) correspondent à `opcua_mapping`.
- 🟠 **P6 : FUXA possède un device `MBTCP_RINCAGE` actif qui interroge directement le simulateur (`192.168.20.10:502`)**, avec des tags de test M0, M1 et M20. La supervision court-circuite l'automate et lit le VLAN terrain, ce qui contredit l'architecture des spécifications. À supprimer, ou au minimum désactiver. Les devices `test` et `test1` sont à nettoyer. [vue.json](../configurations/conteneurs/scada-dev/vue.json) concerne un autre synoptique (« Distribution parallèle ») et `projet.json` est vide.

### 5.2 Logique et physique comparées aux spécifications

| # | Impact | Constat | Où |
|---|---|---|---|
| P1 | 🔴 | **Vidange infinie.** Le pH ne fait que baisser dans le simulateur : aucun apport d'acide neuf ne le remonte. Une fois sous 5.0, l'automate vide jusqu'à 5 %, quitte la vidange, puis y **rentre au cycle suivant** car le pH est toujours < 5. La vanne reste ouverte, la pompe ne redémarre jamais et la production est bloquée. Le récapitulatif prévoit pourtant un « retour à pH 7.0 » après régénération. Correctif côté simulateur : modèle de mélange au remplissage, par exemple `pH = (V·pH + dV·7.0)/(V+dV)`, ou retour à 7.0 si la cuve est vidée sous un seuil. | [moteur_physique.py:100-112](../configurations/conteneurs/sim/rincage/moteur_physique.py#L100-L112), [logique.py:63-72](../configurations/conteneurs/api/rincage/logique.py#L63-L72) |
| P2 | 🟠 | **Défaut en mode manuel** : la spécification dit que le défaut débordement coupe *tous* les actionneurs « prévalant sur tout ordre de conduite (manuel ou automatique) ». Le code laisse l'opérateur piloter en manuel malgré le défaut (choix commenté : « pour pouvoir dépanner »), avec seulement un verrou sur la pompe. C'est défendable, mais **le code et la spécification doivent dire la même chose**. | [logique.py:30-36, 85-96](../configurations/conteneurs/api/rincage/logique.py#L30) |
| P3 | 🟠 | **Acquittement sur niveau et non sur front.** La spécification parle d'*impulsion*. Si le bouton FUXA reste à `True`, tout défaut futur est acquitté automatiquement dès que l'alarme disparaît. L'automate ne remet jamais `AcquittementDefaut` à `False`. Il faut détecter le front montant et faire le reset par l'automate. | [logique.py:27](../configurations/conteneurs/api/rincage/logique.py#L27) |
| P4 | 🟠 | **L'information « État cycle » demandée par l'IHM (Rinçage / Vidange chimique) n'est pas exposée** : `mode_vidange` reste interne. Il faut ajouter un tag `Systeme.EtatCycle` ou `VidangeEnCours`. | [config_api.json](../configurations/conteneurs/api/rincage/config_api.json) |
| P5 | 🟡 | Seuil de pH incohérent entre documents : **5.0** (spécifications et code) contre **5.5** (récapitulatif). | PDF |
| P7 | 🟡 | `initial_state.niveau_acide = 50` est ignoré : `volume_reel` démarre à 0 et écrase le niveau au premier pas. `pieces_dans_tambour` n'est pas utilisé. | [moteur_physique.py:18](../configurations/conteneurs/sim/rincage/moteur_physique.py#L18) |
| P8 | 🟡 | Perte du Modbus : aucun défaut de communication n'est levé, seul `ConnexionSimuOk` passe à False. Un vrai automate passerait en repli. À spécifier. | [app.py](../configurations/conteneurs/api/rincage/app.py) |
| P9 | 🟡 | Le client Modbus de l'automate a **des adresses en dur** (10/3, 20/2, coils 0–5), alors que le simulateur est piloté par `modbus_mapping`. Pour un banc générique, l'automate devrait lire le même contrat d'échange (fichier partagé, qui pourrait vivre dans `/srv/sii/infra`). | [client_modbus.py:28-59](../configurations/conteneurs/api/rincage/client_modbus.py#L28-L59) |
| P10 | 🟡 | Les seuils (40/80 %, pH 5, vidange 5 %) sont codés en dur. La spécification IHM prévoit de les rendre paramétrables : à passer en config et/ou en tags OPC-UA. Les détections et le compteur de pièces ne sont pas exposés, alors qu'ils seraient utiles comme indicateurs de production pour les tests. | [logique.py](../configurations/conteneurs/api/rincage/logique.py) |

---

## 6. Reproductibilité (reconstruire la plateforme depuis le repo)

| # | Impact | Constat |
|---|---|---|
| R1 | 🔴 | [sim/rincage/requirements.txt](../configurations/conteneurs/sim/rincage/requirements.txt) est **vide** : une reconstruction produit une image sans `pymodbus`. |
| R2 | 🟠 | `pymodbus>=3.6.8` n'est pas figé, et les deux images utilisent des API **incompatibles** : l'automate utilise `device_id=` (pymodbus ≥ 3.10), le simulateur `ModbusSlaveContext` et `zero_mode` (API < 3.10). Il faut figer une version par image, ou mieux migrer les deux sur la même. |
| R3 | 🟠 | **Build manuel, non documenté.** Les images sont construites sur Docker Desktop (émulation arm), exportées en `.tar` puis importées à la main en SSH sur chaque Pi. Les tags sont incohérents (`simu-rincage-image:latest` dans le compose contre `sim-rincage.tar`) et il n'y a pas de versionnage. Cible, cohérente avec la règle « tout passe par pi5X » : un script de build (`buildx --platform linux/arm64`, tag versionné) qui **publie le `.tar` dans `/srv/sii/infra/images` sur pi51**. La synchro et l'agent de nœud font le reste : plus d'import manuel nœud par nœud. |
| R4 | 🟡 | Images de base non figées (`alpine:latest`, `frangoteam/fuxa:latest`). `version: '3.8'` est obsolète dans les compose. |
| R5 | 🟡 | Scripts dupliqués par machine (`installation_docker.sh` et `creation_vlan.sh` sont identiques sur les 3 Pi), code obsolète ([autres/installation.sh](../configurations/autres/installation.sh), `old*`, `sav/`), [readme.md](../readme.md) racine vide. |
| R6 | 🟡 | `fuxa_appdata/` est ignoré dans `.gitignore` mais ses fichiers sont suivis par Git : le comportement est ambigu. Le projet SCADA mérite d'être versionné explicitement, en export JSON. |

---

## 7. Aptitude à servir de banc de test

**Points d'appui** : configs JSON par brique, cloisonnement par VLAN, IaaC visualisable. Brancher une nouvelle brique **passive** (sonde IDS sur un port miroir, client OPC-UA, historian) est simple.

**Freins actuels** :
- Il n'y a pas de **contrat d'échange unique** par procédé (P9) : un deuxième procédé demanderait de recoder le client Modbus.
- Il n'y a pas de **matrice de flux** (§2.2) : impossible de valider automatiquement qu'une brique de filtrage laisse passer exactement ce qu'il faut.
- Le **déploiement est manuel et dupliqué** (§2.3) : chaque nouvelle brique ajoute des points de divergence.
- Il n'y a **aucun test automatisé** du procédé (le dossier `tests/` ne contient que des clients manuels) : une non-régression après modification de la logique est impossible.

---

## 8. Plan d'action

Les phases sont ordonnées par dépendance. La phase 1 correspond à votre objectif prioritaire. Les estimations sont indicatives, pour une personne.

### Phase 0 : Remise à plat (≈ ½ journée, sans risque)
- [ ] Commiter le travail en cours (`hote_parent` en liste) et aligner `schema.json` (I3, I9).
- [ ] Corriger `infrastructure.json` : `eth0.10` et liaison switch pour pi51 (I1), VLAN de `ha-cluster` (I4), `port2` (I6), `depot_source` et `chemin_deploiement` (I7, I8).
- [ ] Remplir et figer `requirements.txt` des deux images (R1, R2).
- [ ] Vérifier sur pi31 l'absence de `test-opcua-srv` (D11).
- [ ] Désactiver le device Modbus direct dans FUXA (P6).
- [ ] Trancher les écarts entre schéma et IaaC (S1 à S4 : port 4, VLAN30 sur le trunk de pi31, placement de `scada1`), puis corriger la source qui a tort.

### Phase 1 : Serveur de données et réplication par VLAN (objectif prioritaire)
- [ ] Ajouter la section `clusters` à l'IaaC (fonctionnel : pi31, pi32 ; infra : pi51), car les cibles de réplication en dépendent (§1.1).
- [ ] Définir et documenter l'arborescence `/srv/sii/{infra,vlan20,vlan30}` commune à tous les nœuds (§3.3), et la décrire dans l'IaaC (nouvelle section `stockage` : partages, sources, cibles = membres du cluster fonctionnel, périmètre).
- [ ] Rendre l'agent de synchronisation générique : cibles et chemins en variables d'environnement, transport sur le VLAN10, `--mkpath`, `ConnectTimeout`, cibles indépendantes, `--delay-updates`, `.sync_status.json`, healthcheck Docker.
- [ ] Ajouter l'agent `sync-infra` (plan d'administration).
- [ ] Aligner le FTP : création explicite du sous-dossier synchronisé, documentation de la convention de dépôt (D8), correction du readme (D10).
- [ ] Mettre à jour les scripts de déploiement pour qu'ils lisent leurs paramètres depuis l'IaaC (premier pas vers la génération).
- [ ] Dérouler la recette §3.4.

### Phase 2 : HA adossée à la source unique
- [ ] Séparer gestionnaire (cluster infra, pi51 : génération et publication de l'état voulu, collecte de l'état réel) et agent de nœud (pi3X : application, VRRP, bascule autonome) (H10).
- [ ] Agent HA : montage `/srv/sii:/srv/sii:ro`, services lancés depuis `/srv/sii/infra/services/<svc>` (H1), images depuis `/srv/sii/infra/images` (H8).
- [ ] `nopreempt` (ou retour manuel) (H2), sonde **par service** (H3), priorité par nœud (H7).
- [ ] Groupes de bascule distincts : simulation / automate / SCADA (H5).
- [ ] Préparer le cluster de supervision : VLAN dédié dans l'IaaC, projet FUXA publié comme artefact dans `/srv/sii/<périmètre supervision>`, données d'exécution (alarmes, historiques) locales ou sur un futur historian. En attendant, documenter le flux poste .49 → 192.168.30.20:4840.
- [ ] Protection contre le double maître : contrôle de l'IP de service avant démarrage (H6).
- [ ] Documenter la bascule à froid (H4) et décider d'une éventuelle mémoire rémanente.
- [ ] Scénarios de recette : arrêt de pi31, arrêt de `api-rincage`, coupure du VLAN10, retour de pi31.

### Phase 3 : Fidélité du procédé
- [ ] Régénération du pH dans le simulateur (P1), le plus urgent fonctionnellement : peut être avancé en phase 0.
- [ ] Acquittement sur front (P3), tag `EtatCycle` (P4), alignement code/spécifications sur le défaut en manuel et le seuil de pH (P2, P5).
- [ ] État initial du simulateur (P7), défaut de communication (P8).
- [ ] Contrat d'échange Modbus partagé (P9), seuils paramétrables (P10).
- [ ] Tests unitaires de `logique.py` (fonction pure, très facile à tester) et test d'intégration simulateur + automate.

### Phase 4 : IaaC prescriptive
- [ ] Corriger le générateur netplan : route et DNS sur les VLANs virtuels (I2) ; générer aussi la création des réseaux macvlan.
- [ ] Ajouter au modèle : SCADA et VLAN de supervision, poste d'administration .49, `srv1`, réseaux Docker et IPAM (H9), **matrice de flux** (avec génération de la checklist pare-feu).
- [ ] Rendu topologique de l'IaaC comme vue technique de référence ; draw.io réduit aux vues conceptuelles (§2.4).
- [ ] Générer depuis `infrastructure.json` : `.env`/compose des services, `config_cluster.json`, paramètres des agents de synchronisation.
- [ ] Validation de `infrastructure.json` contre `schema.json` à l'enregistrement (`serveur.py`).
- [ ] (Avec accès SSH) contrôle de dérive : comparaison de l'IaaC avec l'état réel (`ip a`, `docker ps`, `docker network inspect`).

### Phase 5 : Industrialisation
- [ ] Script de build multi-architecture versionné (arm64) produisant des `.tar` taggés directement dans `infra/images` (R3).
- [ ] Figer les images de base (R4), factoriser les scripts machines (R5), nettoyer le code obsolète, écrire le readme racine.
- [ ] Projet FUXA versionné en export (R6).
- [ ] **Puis audit de sécurité** (FTP en clair, OPC-UA sans sécurité, clés SSH, conteneurs privilégiés, flux inter-zones…).

---

## 9. Questions ouvertes

**Réponses obtenues (2026-11-14)**, intégrées dans le rapport :
- *FUXA* : il tourne sur le poste d'administration 192.168.10.49. À terme, il aura son propre cluster dans un VLAN dédié (§1.1).
- *Build* : Docker Desktop avec émulation arm, export `.tar`, import manuel en SSH (R3).
- *Données* : pi5X (puis son cluster) est la source **unique** de toutes les données de la plateforme. Tout dépôt passe par le dossier du périmètre sur pi5X, puis est synchronisé (§1.1, §3.3, D8).
- *`sim-es-2` / `api2` / `api3`* : ils illustrent seulement la croissance future (§2.2).
- *GIA* : gestion des identités et des accès, rien d'existant aujourd'hui.

**Questions restantes :**
1. Câblage réel du switch : port 1 ou 2 pour l'administration, port 4 vers pi32 ou vers pi51, trunk de pi31 avec ou sans VLAN30, et que représente `srv1` sur le port 5 ?
2. Futur VLAN de supervision : quel numéro et quel plan d'adressage ? Le VLAN30 reste-t-il le réseau d'échange OPC-UA entre automates et supervision ?
3. Défaut en mode manuel : suivre la spécification (tout coupé) ou le code (dépannage possible) ?
4. Seuil de pH : 5.0 ou 5.5 ?
