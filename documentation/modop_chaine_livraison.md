# Mode opératoire : chaîne de livraison locale

| | |
|---|---|
| Date | 2026-11-26 |
| Base | commit `e96e20f` |
| Public | agents Claude Code (VS Code, poste d'administration) et administrateur |
| Règles permanentes | `CLAUDE.md` à la racine : elles priment sur ce document |
| Cible | `documentation/architecture_reference.md` |
| Statut | à exécuter, rien n'est encore fait |

## 1. Objectif et architecture cible

Déployer toute la plateforme depuis des services **locaux** et **préparer** la coupure de son accès à internet.

```text
Internet ── Poste d'administration (SAS) ──────── pare-feu ──── Plateforme (coupure à préparer)
            Claude Code, build des images                       pi51 : registre, dépôt git, Ansible
            import des artefacts                 git push ───▶  pi31, pi32 : tirent leurs images de pi51
                                                 docker push ─▶ pi51
```

| Rôle | Outil | Ne fait pas |
|---|---|---|
| État voulu | NetBox | Ne déploie rien |
| Production des fichiers | `generer.py` | Ne touche pas aux nœuds |
| Historique | git | |
| Images | Registre sur pi51 | Ne les construit pas |
| Application | Ansible, lancé à la demande depuis pi51 | Ne surveille pas, ne bascule pas de lui-même, ne construit pas |
| Haute disponibilité | agent `ha-cluster` (keepalived) | Ne déploie pas |
| Contrôle | `derive.py`, `verifier_chaine_scada.py` | |
| Fichiers métier | FTP et rsync | Plus aucun compose ni image |

Choix de la première version :
- Les images sont **construites sur le sas** (pip, apk, npm y ont internet). La plateforme n'a besoin que des images.
- Ansible tourne sur **pi51** (Linux). Aucun outil serveur supplémentaire sur le poste Windows.
- Dépôt git local : dépôt nu sur pi51, accès SSH. Forge et CI : lot E.
- Si pi51 est arrêté, les déploiements sont impossibles mais le procédé et la HA continuent.

## 2. Accès à internet

Ordre à suivre :

1. ressource locale de la plateforme ;
2. passage par le poste d'administration (télécharger, puis pousser), si c'est simple ;
3. accès direct depuis la plateforme, seulement si indispensable.

Aucun lot n'est bloqué par l'absence de coupure. Les cas 2 et 3 alimentent `documentation/dependances_internet.md`
(à créer au lot 0) :

| Dépendance | Nœud | Usage (installation, déploiement, exécution) | Voie (sas, direct) | Remplacement prévu | Statut |
|---|---|---|---|---|---|

Connues au départ : DNS publics, heure, paquets Ubuntu et Docker, images de base, pip, apk, npm (au build), GitHub.

## 3. Déroulement

Un lot à la fois, une branche par lot, validation de l'administrateur avant le suivant.

| Lot | Contenu | Dépend de |
|---|---|---|
| 0 | État des lieux | |
| A | Registre | 0 |
| B | Images versionnées | A |
| C | Dépôt local, Ansible, fiches de brique | B |
| D | Services de base locaux | C |
| E | NetBox, forge et CI sur la plateforme | C, décision serveur |
| F | Coupure d'internet : préparation et répétition | D, E, sur demande de l'administrateur |
| S | Schéma d'architecture draw.io (documentaire) | 0 |

L'étape 2 (UNS) peut commencer après le lot C. La zone du niveau 3 (référence, D7) se décide à ce moment-là : aucun
lot de ce document ne crée de VLAN.

## Lot 0 : état des lieux (lecture seule)

1. Mettre à jour le graphe graphify, relire les dernières entrées du journal.
2. `git status`, garde-fou actif, les deux suites de tests, `synchro.py --verifier`.
3. `collecte.sh` sur les trois Pi puis `derive.py`.
4. Relever sur pi51 : `free -h`, `df -h`, `docker info`. Sur chaque Pi : `cat /etc/docker/daemon.json`.
5. Vérifier que le poste d'administration et les Pi atteignent `192.168.10.12`.
6. Créer le registre des dépendances (§2). Confronter l'existant à l'architecture de référence et signaler les écarts
   absents de son §7.
7. Relever la **référence de non-régression** (§4) et la consigner dans le journal.

**Arrêt** si un écart ou un test en échec : le signaler avant de continuer.

## Lot A : registre d'images

1. Migration `netbox/migrations/AAAA-MM-JJ_registre.py` (idempotente, sur le modèle de `2026-11-23_conduite_scada.py`) :
   service `registre`, cluster `infra`, chemin `registre`, image `registry:3` (figer la version exacte retenue),
   `restart: unless-stopped`, `ports: ["192.168.10.12:5000:5000"]`, volume `./data:/var/lib/registry`, port TCP 5000
   avec clients `poste-admin`, `pi31`, `pi32`.
2. Corriger la matrice de flux dans `generer.py` : un service publié sur l'hôte (sans IP macvlan) y apparaît avec
   `None`. Ajouter un test dans `netbox/tests/test_outils.py`.
3. `synchro.py`, relire le diff, publier sur pi51, `docker compose up -d` dans `~/registre`.
4. Sur pi51, pi31, pi32 : ajouter à `/etc/docker/daemon.json` (en fusionnant avec l'existant)
   `{ "insecure-registries": ["192.168.10.12:5000"] }`, valider le JSON, puis `sudo systemctl reload docker`.
   **Jamais `restart`** : il arrêterait le procédé. Passif d'abord.
5. Même réglage dans Docker Desktop (son redémarrage est sans effet sur la plateforme ; il arrête NetBox : le vérifier
   ensuite).

**Recette** : `docker info` mentionne le registre sur chaque machine ; une image de test arm64 poussée depuis le sas est
tirée par pi32 ; conteneurs inchangés ; `curl http://192.168.10.12:5000/v2/_catalog` répond ; registre de retour après
un redémarrage de pi51 (avec accord) ; 0 écart.

**Retour arrière** : retirer le service par migration, restaurer `daemon.json`, `reload`.

## Lot B : images versionnées

1. `configurations/construire_images.sh` : une version explicite par image, tag
   `192.168.10.12:5000/sii/<nom>:<version>`, `docker push` à la place de `docker save`. Une version publiée n'est
   jamais réécrite.
2. Figer `alpine:latest` (serveur FTP, agent de synchro). Traiter `scada-dev` (`fuxa:latest`) : figer ou retirer.
3. Copier dans le registre les images de base et tierces en `linux/arm64` (dont `registry`), et en garder une archive
   `.tar` hors git pour reconstruire pi51.
4. NetBox (migration) : remplacer les images par leur nom complet versionné, service par service.
5. Ordre : SCADA, puis services de données, puis cluster fonctionnel (procédure HA du §5).

**Recette** : chaque conteneur utilise une image du registre, `derive.py` 0 écart, chaîne SCADA validée.

**Retour arrière** : remettre l'ancien nom d'image dans NetBox (images conservées sur les nœuds jusqu'à la fin du lot).

Le chargeur `auto_loader.sh` et le dépôt `~/images` ne sont retirés qu'après la recette du lot C.

## Lot C : dépôt local et Ansible

1. Créer le dépôt nu `~/git/sii.git` sur pi51 ; ajouter sur le sas le remote `plateforme`. Copie de travail sur pi51,
   mise à jour par `git pull --ff-only` uniquement : on n'y édite rien.
2. Installer Ansible sur pi51 dans un environnement Python dédié, version figée. Documenter la reconstruction de pi51
   depuis le sas.
3. Clé SSH dédiée de pi51 vers pi31 et pi32 (distincte de la clé de synchro). Mode d'élévation `sudo` : **à décider par
   l'administrateur**.
4. Dossier `ansible/` avec son README :
   - `inventaire/` **généré** par `generer.py` depuis le modèle, versionné et contrôlé par `synchro.py --verifier` ;
   - `socle.yml` : Docker, `daemon.json`, mises à jour automatiques désactivées, réseaux macvlan ;
   - `deployer.yml` : fichiers de `configurations/machines/<nœud>/`, amorçage **sans écrasement**, `pull`, puis `up -d`
     (services simples) ou procédure HA (§5).
5. Netplan et pare-feu restent manuels. Les `.env` ne sont ni créés ni écrasés ; leur absence fait échouer le playbook.
6. Valider par `--syntax-check`, puis `--check --diff` (ses limites avec les tâches de commande sont à noter), puis
   exécution sur pi51, puis sur le cluster fonctionnel.
7. Ajouter à chaque brique existante sa **fiche** et sa classe (référence, §5), à partir du code et de NetBox.

**Recette** : second passage de `socle.yml` sans changement ; une nouvelle version de l'automate déployée en une
commande, sans doublon d'IP ; arrêt propre si le passif échoue (à tester avec un tag inexistant).

**Retour arrière** : `publier.sh` reste utilisable tant que la recette n'est pas acquise.

## Lot D : services de base locaux

| Dépendance actuelle | Cible |
|---|---|
| DNS `1.1.1.1` et `8.8.8.8` (modèle, netplan) | Résolveur local (pfSense ou pi51), modifié dans NetBox ; netplan appliqué à la main avec `netplan try` |
| Heure par Internet (chrony, NTS) | chrony sur pi51 comme serveur ; source de temps sans internet à décider (horloge RTC sauvegardée, source matérielle) |
| `download.docker.com` et dépôts Ubuntu (`installation_docker.sh`) | Cache ou miroir local contenant tous les paquets nécessaires à une réinstallation |
| Images tierces | Registre (lot B) |
| Liens GitHub dans `iaac/` (`vers_iaac.py`) | Dépôt local |
| Sauvegardes | Registre, dépôt git, export NetBox, données FUXA : copie hors de pi51, restauration testée |

Traiter d'abord ce qui touche l'exécution (DNS, heure). Un miroir de paquets n'est monté que si le passage par le
sas ne suffit pas. Un simple cache ne garantit pas la présence d'un paquet jamais demandé.

## Lot E : NetBox, forge et CI sur la plateforme

NetBox, source de vérité, tourne aujourd'hui sur le poste d'administration, hors plateforme.

1. **Décision préalable** : hébergement sur un serveur dédié (recommandé) ou sur pi51, selon la RAM relevée au lot 0.
2. Migrer NetBox : sauvegarde de la base, restauration, `exporter.py --comparer` à 0 écart, ancienne instance arrêtée.
   Secrets de démonstration hors git.
3. Forge locale (Forgejo) et son runner, installés depuis le sas. Les actions des workflows doivent être résolues
   **localement** (`DEFAULT_ACTIONS_URL`), pas depuis internet.
4. CI : deux suites de tests et `synchro.py --verifier`.

## Lot F : coupure d'internet (préparation et répétition)

À lancer à la demande de l'administrateur. La répétition est temporaire et réversible.

1. Avec l'administrateur, bloquer sur pfSense la sortie internet des VLAN 10, 20 et 30. Noter la règle pour revenir.
2. Redémarrer à froid les nœuds ; réinstaller pi32 de zéro ; déployer une nouvelle version ; basculer.
3. Vérifier heure, DNS, registre, dépôt, NetBox, CI.
4. Tout échec : noter la dépendance, rétablir si nécessaire, corriger, rejouer.

**Terminé** quand le scénario passe, avec pour seules exceptions les dépendances acceptées au registre.

## Lot S : schéma d'architecture

Améliorer `documentation/archi_plateforme.drawio`, aujourd'hui périmé (audit §2.4, S1 à S6). Aucun impact sur la
plateforme.

| Page | Contenu | Source |
|---|---|---|
| Physique (réel) | Matériels, ports, câblage, trunks, pare-feu, poste d'administration | `sii.yaml`, confirmé par l'administrateur pour le câblage |
| Logique (réel) | VLAN, nœuds, conteneurs, IP, VIP, clusters, flux applicatifs | `sii.yaml`, relevés `collecte.sh` |
| Cible | Niveaux ISA-95, zones et conduits, chaîne de déploiement, UNS | `architecture_reference.md` |

- Le réel ne montre que l'existant vérifié. Sur la page Cible, distinguer « existant », « prévu » et « envisagé »
  (VLAN40, en pointillés) par le trait, avec une légende.
- NetBox reste la référence : chaque page porte la date et le commit de sa source. En cas d'écart entre NetBox et le
  terrain, le signaler au lieu de choisir.
- Pages lisibles : une idée par page, mêmes formes et couleurs partout. Conserver le format draw.io non compressé.

**Recette** : fichier XML valide, ouvert dans draw.io par l'administrateur ; chaque nœud, IP et VLAN recoupé avec
`sii.yaml` ; constats S1 à S6 traités un par un ; `documentation/README.md` et suivi d'audit à jour.

## 4. Non-régression et fonctionnement

**Avant** le changement, jouer les contrôles et noter les résultats. **Après**, les rejouer : aucun résultat ne doit se
dégrader.

| Contrôle | Commande ou geste | Quand |
|---|---|---|
| Tests hors ligne | `python -m unittest discover -s tests`, à la racine et dans `netbox/` | Tout changement |
| Cohérence du dépôt | `synchro.py --verifier`, NetBox joignable | Tout changement |
| Conformité des nœuds | `collecte.sh` puis `derive.py` : 0 écart | Plateforme touchée |
| Chaîne de conduite | `verifier_chaine_scada.py` (lecture seule) | Plateforme touchée |
| Commande jusqu'au procédé | `verifier_chaine_scada.py --marche`, avec accord | Automate, simulateur, SCADA, réseau, HA |
| Haute disponibilité | Une seule VIP, services actifs sur le maître seul | Plateforme touchée |
| Bascule dans les deux sens | Avec accord, sans doublon d'IP | Lots A à C si le cluster est touché, lot F |
| Fichiers métier | Dépôt FTP d'un fichier témoin, présence sur le nœud destinataire, puis retrait | Services de données, réseau, pi51 |

- Aucun test automatisé ne couvre la HA ni les fichiers métier : consigner la commande et le résultat observé.
- Un composant nouveau a un test de fonctionnement : nominal, redémarrage, dépendance absente.
- Les recettes de chaque lot s'ajoutent à ces contrôles.
- En cas de régression : arrêter, appliquer le retour arrière, vérifier le retour à la référence, tracer.
- Un lot est clos quand sa recette et ces contrôles sont passés, ou que l'administrateur a accepté par écrit ce qui
  ne l'est pas.

## 5. Procédure de déploiement sur le cluster en HA

Accord de l'administrateur requis : la bascule redémarre le procédé à froid.

1. Vérifier l'état sain et qu'**un seul** nœud porte la VIP `192.168.10.251`. Sinon, arrêter.
2. Passif : fichiers, `docker compose pull`, `docker compose create` (automate, simulateur). Si l'agent change :
   `docker compose up -d` dans `~/ha-cluster`, puis vérifier qu'il reste passif.
3. Vérifier les images et les conteneurs créés, arrêtés. En cas d'échec, arrêter ici.
4. Maître : `docker stop ha-cluster`.
5. Vérifier sur le nouveau maître : VIP, automate et simulateur démarrés ; arrêtés sur l'ancien.
6. Ancien maître : fichiers, `pull`, `create`, puis `docker compose up -d` dans `~/ha-cluster`.
7. Avec accord : « Marche » (`verifier_chaine_scada.py --marche`). Puis `collecte.sh` et `derive.py`.

Pas de retour automatique sur pi31 (`nopreempt`) : retour au nominal par une bascule explicite.

**Retour arrière** : remettre la version précédente dans NetBox et rejouer la procédure.

## 6. Compte rendu attendu à la fin de chaque lot

Court : une ligne par point.

- Fait et vérifié (commande et résultat, avant et après).
- Non vérifié ou supposé.
- Incidents et écarts par rapport à ce document (le corriger dans le même lot).
- Commits, entrée du journal, README mis à jour.
- Décisions attendues de l'administrateur.
