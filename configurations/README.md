# Configurations : code des conteneurs et préparation des nœuds

Ce dossier contient **ce qui ne vient pas de NetBox** : le code et les Dockerfile des images, les configurations
des applications, la préparation des nœuds. Les fichiers de **déploiement** (docker-compose, netplan, réseaux
macvlan, `config_cluster.json`) ne sont plus ici : ils sont générés depuis NetBox (`netbox/genere/`).

## Briques de la plateforme

| Dossier | Image | Rôle | Nœuds |
|---|---|---|---|
| [`conteneurs/api/rincage/`](conteneurs/api/rincage/README.md) | `api-rincage-image` | Automate logiciel : Modbus vers le simulateur, serveur OPC-UA vers le SCADA | pi31, pi32 (HA) |
| [`conteneurs/sim/rincage/`](conteneurs/sim/rincage/README.md) | `simu-rincage-image` | Simulateur physique du tambour de rinçage (serveur Modbus) | pi31, pi32 (HA) |
| [`conteneurs/cluster/`](conteneurs/cluster/README.md) | `agent-ha` | Agent de haute disponibilité (keepalived, VRRP) | pi31, pi32 |
| [`conteneurs/scada/`](conteneurs/scada/README.md) | `scada-fuxa:1.3.3` | SCADA FUXA, IHM de conduite | pi51 (cluster conduite) |
| [`conteneurs/donnees/`](conteneurs/donnees/readme.md) | `serveur-ftp`, `agent-sync` | Ingestion FTP et réplication rsync des données par VLAN | pi51 |
| [`machines/`](machines/README.md) | — | Préparation d'un nœud (Docker, mises à jour) | tous |

## Construire les images

Les Pi sont en arm64 ; les images sont construites sur le poste d'administration (Docker Desktop, `buildx` avec
émulation arm64) puis exportées en `.tar` dans `configurations/images/` (hors git) :

```sh
sh configurations/construire_images.sh              # toutes
sh configurations/construire_images.sh agent-ha     # une seule
```

Les versions des images de base et des dépendances sont figées (audit R2, R4). Chaque dossier a un
`.dockerignore` : les anciennes images `.tar` ne doivent jamais entrer dans une image.
Déploiement d'une image : voir `netbox/README.md` (dépôt dans `~/images` des nœuds, chargement par l'agent HA).

## Hors plateforme (archives et essais)

Conservés pour l'historique, **non déployés**, à trier :
`conteneurs/api/old/`, `conteneurs/sim/old_cuve_pression/`, `conteneurs/opcua-srv/` (serveur OPC-UA de test),
`raps1/`, `machines/pi3x/opcua-srv.sh`, et `conteneurs/scada-dev/` (instance FUXA de développement du poste
d'administration, gardée pour des essais : elle n'est pas la référence, voir `conteneurs/scada/`).
