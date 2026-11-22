# NetBox, source de vérité de la plateforme SII

NetBox décrit l'état voulu de la plateforme : équipements, câbles, VLAN, IP, clusters, VIP, services et flux.
Les fichiers de déploiement (netplan, réseaux macvlan, docker-compose, `config_cluster.json`) sont **générés**
depuis NetBox, jamais écrits à la main.

```text
            importer.py                 exporter.py               generer.py              publier.sh
donnees/sii.yaml ──────────▶ NetBox ──────────▶ donnees/sii.yaml ──────────▶ genere/ ──────────▶ pi31, pi32, pi51
 (pré-rempli)            (fait foi)        (copie git)                                  │
                                                                                         ▼
                                   derive.py ◀────────── collecte/*.json ◀──── collecte.sh (état réel)
```

## Contenu

| Fichier | Rôle |
|---|---|
| `donnees/sii.yaml` | Modèle pré-rempli depuis `iaac/infrastructure.json`, avec les corrections de l'audit (I1 à I9). Contient la liste `a_verifier`. |
| `outils/modele.py` | Valide le modèle (IP en double, VLAN, câbles, clients…). Fonctionne hors ligne. |
| `outils/importer.py` | Charge le modèle dans NetBox. Relançable sans créer de doublons. |
| `outils/exporter.py` | Relit NetBox au même format. `--comparer` vérifie l'aller-retour. |
| `outils/generer.py` | Produit `genere/<noeud>/…`, `genere/matrice_flux.md`, `genere/topologie.html` (vue graphique) et `genere/publier.sh`. |
| `outils/collecte.sh` | Relève l'état réel d'un nœud en JSON (lecture seule). |
| `outils/derive.py` | Compare l'état réel au modèle. |
| `deploiement/docker-compose.override.yml` | Réglages locaux pour `netbox-docker`. |
| `tests/` | Tests hors ligne. Ils prouvent notamment que le modèle redonne à l'identique les netplan, compose et `config_cluster.json` actuels. |

Prérequis sur le poste d'administration : Python 3.11+, `pip install -r outils/requirements.txt`, Docker Desktop.
Toutes les commandes se lancent depuis `netbox/`.

## Avant le démarrage (plateforme éteinte)

```sh
python -m unittest discover -s tests      # 19 tests, tous verts
python outils/modele.py                   # 0 erreur ; liste les avertissements et les points à vérifier
python outils/generer.py -o genere/       # aperçu des fichiers qui seront déployés
```

Les étapes 2 à 4 n'ont pas besoin des Pi : elles peuvent être faites dès maintenant sur le poste d'administration.

## Jour J (première mise en service)

> Réalisé le 2026-11-22, avec des écarts de procédure : voir `documentation/journal_exploitation.md`.
> Pour l'exploitation au quotidien, voir plus bas **Exploitation courante**.

### 1. Relever l'état réel et finir le modèle

```sh
mkdir -p collecte
ssh pi31@192.168.10.10 sh -s < outils/collecte.sh > collecte/pi31.json
ssh pi32@192.168.10.11 sh -s < outils/collecte.sh > collecte/pi32.json
ssh pi51@192.168.10.12 sh -s < outils/collecte.sh > collecte/pi51.json
python outils/derive.py collecte/
```

Pour chaque `ÉCART`, décider qui a raison :
- **la machine** (exemple : le vrai dossier d'un docker-compose) : corriger `donnees/sii.yaml` ;
- **le modèle** (exemple : un vieux conteneur `test-opcua-srv`, audit D11) : laisser, l'étape 7 le corrigera.

Régler aussi la liste `a_verifier` (câblage du commutateur, pare-feu, port de pi51…), puis la vider.
C'est la **dernière fois** que `sii.yaml` est édité à la main.
Vérifier ensuite que `python outils/modele.py` affiche bien 0 erreur.

### 2. Démarrer NetBox

```sh
git clone -b release https://github.com/netbox-community/netbox-docker.git
cp netbox/deploiement/docker-compose.override.yml netbox-docker/
cd netbox-docker
docker compose pull && docker compose up -d          # premier démarrage : plusieurs minutes
docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser
```

Ouvrir http://localhost:8000, se connecter, puis aller dans le profil → **API Tokens** → créer un jeton en écriture.

Avant toute utilisation durable, changer les secrets de démonstration de `env/*.env` (`SECRET_KEY`, mots de passe de
la base et de Redis, `API_TOKEN_PEPPER_1`).

### 3. Importer

```sh
export NETBOX_URL=http://localhost:8000
export NETBOX_TOKEN='nbt_<clé>.<jeton>'      # jeton complet tel qu'affiché par NetBox
python outils/importer.py
python outils/importer.py                    # 2e passage : doit annoncer 0 création
```

### 4. Contrôler l'aller-retour, puis basculer la source de vérité

```sh
python outils/exporter.py --comparer donnees/sii.yaml     # doit annoncer 0 écart
python outils/exporter.py -o donnees/sii.yaml             # NetBox fait foi désormais
git add donnees/sii.yaml && git commit -m "SII : source de vérité dans NetBox"
```

### 5. Générer et relire

```sh
python outils/generer.py -o genere/
```

- Relire `genere/matrice_flux.md` : chaque ligne « Pare-feu : oui » demande une règle sur le pare-feu.
- Comparer avec ce qui est déployé, par exemple :
  `ssh pi31@192.168.10.10 cat ~/api/rincage/docker-compose.yml | diff - genere/pi31/api/rincage/docker-compose.yml`

### 6. Publier sur les nœuds

```sh
sh genere/publier.sh               # liste ce qui serait copié, sans rien toucher
sh genere/publier.sh --appliquer   # copie dans ~ de chaque nœud ; les fichiers remplacés sont gardés (~1~)
```

Sur **pi51**, avant de relancer les FTP, créer le mot de passe à côté de chaque compose (il n'est pas stocké dans NetBox) :

```sh
echo 'FTP_PASS=<mot de passe>' > ~/donnees-vlan-20/.env && chmod 600 ~/donnees-vlan-20/.env
echo 'FTP_PASS=<mot de passe>' > ~/donnees-vlan-30/.env && chmod 600 ~/donnees-vlan-30/.env
```

### 6 bis. Images corrigées

Quatre images portent des correctifs de l'audit (détail dans `documentation/audit_fonctionnel.md`, §10) :

| Image | Correctifs | Nœuds |
|---|---|---|
| `api-rincage-image` | coupure de sécurité sur lecture Modbus incomplète, fin de la vidange infinie, `pymodbus` figé | pi31, pi32 |
| `simu-rincage-image` | régénération du pH par l'acide neuf, niveau initial respecté | pi31, pi32 |
| `agent-ha` | images lues seulement dans `~/images`, pas d'arrêt du procédé au démarrage de l'agent, sonde par service | pi31, pi32 |
| `agent-sync` | synchro suspendue si la source est vide, délai de connexion de 5 s | pi51 |

Les `.tar` sont construits d'avance par `sh configurations/construire_images.sh` (dossier `configurations/images/`,
hors git). Les copier :

```sh
ssh pi31@192.168.10.10 mkdir -p images ; ssh pi32@192.168.10.11 mkdir -p images
for n in pi31@192.168.10.10 pi32@192.168.10.11; do
  scp ../configurations/images/api-rincage.tar ../configurations/images/sim-rincage.tar ../configurations/images/agent-ha.tar $n:images/
done
scp ../configurations/images/agent-sync.tar pi51@192.168.10.12:
```

Les images sont chargées à la main à l'étape 7 : les agents HA y sont arrêtés.

### 7. Appliquer : fenêtre de maintenance

Le cluster est arrêté entièrement puis redémarré avec le nouvel agent. Mettre à jour un agent HA en marche
déclencherait des bascules en cascade (préemption, audit H2) et un risque de doublon d'IP sur le terrain.

**7.1 pi51** (indépendant du cluster) :

```sh
sudo install -m 600 ~/99-pi51-netplan.yaml /etc/netplan/ && sudo netplan try   # Entrée pour confirmer ; sinon retour arrière en 120 s
sh ~/creation_vlan.sh
docker load -i ~/agent-sync.tar
for d in donnees-vlan-20 donnees-vlan-30 sync-vlan-20 sync-vlan-30; do (cd ~/$d && docker compose up -d); done
docker ps
```

Si `derive.py` montrait un service lancé depuis un autre dossier, faire d'abord `docker compose down` dans l'ancien
dossier : sinon le nom du conteneur est déjà pris.

**7.2 Arrêter le cluster fonctionnel**, dans cet ordre (le passif d'abord, sinon il prend la main) :

```sh
ssh pi32@192.168.10.11 'docker stop ha-cluster; docker stop api-rincage sim-rincage 2>/dev/null; docker ps'
ssh pi31@192.168.10.10 'docker stop ha-cluster api-rincage sim-rincage; docker ps'
```

`docker ps` ne doit plus montrer ni `ha-cluster`, ni `api-rincage`, ni `sim-rincage` sur les deux nœuds.

**7.3 Sur pi31 puis sur pi32** (réseau, images, conteneurs créés **sans** démarrer) :

```sh
sudo install -m 600 ~/99-$(hostname)-netplan.yaml /etc/netplan/ && sudo netplan try
sh ~/creation_vlan.sh
for t in ~/images/*.tar; do docker load -i "$t"; done
for d in api/rincage simulation/rincage ha-cluster; do (cd ~/$d && docker compose create); done
```

`docker compose create` recrée les conteneurs avec les nouvelles images, sans les démarrer.

**7.4 Redémarrer le cluster** : l'agent de pi31 d'abord, il devient maître et démarre l'automate et le simulateur.

```sh
ssh pi31@192.168.10.10 'docker start ha-cluster'
# attendre 10 s
ssh pi31@192.168.10.10 'docker ps; ip -4 addr show eth0.10'      # api-rincage, sim-rincage, ha-cluster ; VIP .251
ssh pi32@192.168.10.11 'docker start ha-cluster'
# attendre 10 s
ssh pi32@192.168.10.11 'docker ps'                                # ha-cluster SEUL, pas de VIP
```

Puis relancer le procédé (« Marche ») depuis FUXA.

**7.5 Test de bascule** (recommandé) :

```sh
ssh pi31@192.168.10.10 'docker stop api-rincage'
```

Attendu, en quelques secondes : pi32 prend la VIP et démarre l'automate et le simulateur, pi31 arrête son simulateur.
pi31 ne reprend **pas** la main tout seul (`nopreempt`, audit H2) : voir « Revenir sur le nœud nominal ». Vérifier avec `docker ps` et
`ip -4 addr show eth0.10` sur les deux nœuds, puis relancer « Marche » dans FUXA : une bascule repart à froid (audit H4).

### 8. Contrôle final : tout est d'équerre

```sh
ssh pi31@192.168.10.10 sh -s < outils/collecte.sh > collecte/pi31.json   # idem pi32, pi51
python outils/derive.py collecte/                                        # 0 écart
```

Les lignes `INFO` sont normales : la VIP présente sur le maître, et les services HA arrêtés sur le passif.

## Exploitation courante

### Comportement de la haute disponibilité

| Situation | Ce que fait l'agent HA |
|---|---|
| État normal | Le maître (pi31 en nominal) porte la VIP 192.168.10.251 et fait tourner l'automate et le simulateur. Le passif a ses conteneurs **créés mais arrêtés**. |
| Service planté sur le maître | Sonde en échec deux fois de suite (10 s) : priorité 100 − 20 = 80 < 90, le passif prend la main. |
| Maître éteint ou agent arrêté | L'agent arrête ses services en partant (`notify_stop`), le passif prend la main en 1 à 3 s. |
| Retour d'un nœud | Il reste passif (`nopreempt`) : pas de reprise automatique, donc pas d'aller-retour. |
| Services allumés sur un nœud sans VIP | Le garde-fou les arrête au bout de 20 s (doublon d'IP impossible à faire durer). |

Après chaque bascule, le procédé repart à froid : relancer « Marche » dans FUXA (audit H4).

### Gestes à connaître

- **Basculer volontairement** (maintenance du maître) : `docker stop ha-cluster` sur le maître, puis
  `docker start ha-cluster` quand la maintenance est finie. Il revient en passif.
- **Revenir sur le nœud nominal** (pi31) : même geste sur le maître du moment (pi32).
- **Mettre à jour l'agent** : `cd ~/ha-cluster && docker compose up -d` sur le passif d'abord, puis sur le maître
  (bascule contrôlée).
- **Automate et simulateur** : ne **jamais** faire `docker compose up` dans leurs dossiers, seulement
  `docker compose create` (après un changement d'image ou de compose). C'est l'agent qui les démarre.
- **Nouvelle image** : déposer le `.tar` dans `~/images` du nœud. L'agent la charge dans la minute. Recréer ensuite
  le conteneur (`docker compose create`) sur le passif, puis basculer.

### (Ré)installer un nœud du cluster fonctionnel

Depuis Git Bash, à la racine du repo (exemple : pi31) :

1. Compte et nom d'hôte `pi31`, IP 192.168.10.10. Clé SSH du poste : `ssh-keygen -R 192.168.10.10`, puis copier
   `~/.ssh/id_*.pub` dans `~/.ssh/authorized_keys` du nœud.
2. Docker : `scp configurations/machines/installation_docker.sh pi31@192.168.10.10:` puis `bash installation_docker.sh`.
3. Fichiers générés : `tar -C netbox/genere/pi31 -cf - . | ssh pi31@192.168.10.10 'tar -C ~ --no-overwrite-dir -xf -'`.
4. Configuration des applications, version commitée (fins de ligne Linux) :
   `git show HEAD:configurations/conteneurs/api/rincage/config_api.json | ssh pi31@192.168.10.10 'cat > ~/api/rincage/config_api.json'`
   (idem `config_simu.json` dans `~/simulation/rincage`).
5. Images : `scp configurations/images/{api-rincage,sim-rincage,agent-ha}.tar pi31@192.168.10.10:images/`.
6. Sur le nœud : `sudo install -m 600 ~/99-pi31-netplan.yaml /etc/netplan/ && sudo netplan try`,
   `sh ~/creation_vlan.sh`, `for t in ~/images/*.tar; do docker load -i "$t"; done`,
   `mkdir -p ~/donnees/vlan20/donnees ~/donnees/vlan30/donnees`,
   `docker compose create` dans `~/api/rincage` et `~/simulation/rincage`, puis
   `cd ~/ha-cluster && docker compose up -d` (le nœud démarre passif).
7. Synchro : `ssh pi51@192.168.10.12 'cat ~/.ssh/id_rsa.pub' | ssh pi31@192.168.10.10 'cat >> ~/.ssh/authorized_keys'`.
8. Contrôle : `collecte.sh` puis `derive.py`.

## Ensuite : modifier la plateforme

1. Modifier dans NetBox (interface web ou API).
2. Lancer `python outils/exporter.py -o donnees/sii.yaml`, puis `git diff` pour relire et commiter.
3. Lancer `python outils/generer.py -o genere/`, puis `sh genere/publier.sh --appliquer`, puis appliquer sur le nœud.
4. Lancer `collecte.sh` puis `derive.py` pour vérifier.

Exemple (fait le 2026-11-22) : le délai d'arrêt de l'agent HA (`stop_grace_period: 30s`) a été ajouté dans le
`compose` du contexte local de la VM `ha-cluster` dans NetBox, puis exporté, généré et déployé.

**NetBox fait foi** : ne plus lancer `importer.py` sur `sii.yaml`, il écraserait les modifications faites dans NetBox.

## Hors périmètre

- Les correctifs de l'audit (`documentation/audit_fonctionnel.md`) : le modèle décrit l'existant, sauf les erreurs de
  données I1 à I9.
- Le dossier `iaac/` (`serveur.py`, `index.html`, `schema.json`, `infrastructure.json`) sera remplacé par NetBox.
  Le supprimer une fois l'étape 8 validée.
- Le pare-feu et le commutateur ne sont pas configurés automatiquement : `matrice_flux.md` et les ports décrits
  dans NetBox servent de liste de contrôle.
