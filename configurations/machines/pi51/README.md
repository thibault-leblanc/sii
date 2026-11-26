# pi51

> Dossier **généré** par `netbox/outils/generer.py` depuis NetBox : ne pas le modifier à la main.
> Modifier NetBox, puis `python netbox/outils/synchro.py` ; publier avec `sh netbox/genere/publier.sh`.

| | |
|---|---|
| Rôle | Nœud infra : Stockage central et registre d'images |
| Matériel | Raspberry Pi 5 |
| Système | Ubuntu Server 26.04 |
| Clusters | infra, conduite |
| Accès | `ssh pi51@192.168.10.12` |

## Réseau

| Interface | VLAN | IP | Câble |
|---|---|---|---|
| `eth0` | trunk 10, 20, 30 |  | commutateur/port5 |
| `eth0.10` | 10 | 192.168.10.12/24 |  |
| `eth0.20` | 20 |  |  |
| `eth0.30` | 30 |  |  |

## Services

| Service | Dossier | IP | Démarrage | Image |
|---|---|---|---|---|
| `donnees-vlan-20` (infra) | `~/donnees-vlan-20` | 192.168.20.30 | Docker, toujours | `serveur-ftp:latest` |
| `donnees-vlan-30` (infra) | `~/donnees-vlan-30` | 192.168.30.30 | Docker, toujours | `serveur-ftp:latest` |
| `registre` (infra) | `~/registre` |  | Docker, toujours | `registry:3.1.2` |
| `scada` (conduite) | `~/scada` | 192.168.30.10 | Docker, toujours | `scada-fuxa:1.3.3` |
| `sync-vlan-20` (infra) | `~/agent-sync/sync-vlan-20` | 192.168.20.31 | Docker, toujours | `agent-sync:latest` |
| `sync-vlan-30` (infra) | `~/agent-sync/sync-vlan-30` | 192.168.30.31 | Docker, toujours | `agent-sync:latest` |

## Fichiers de ce dossier

| Fichier | Destination sur le nœud |
|---|---|
| `99-pi51-netplan.yaml` | `/etc/netplan/` : `sudo install -m 600 ~/99-pi51-netplan.yaml /etc/netplan/ && sudo netplan try` |
| `agent-sync/sync-vlan-20/docker-compose.yml` | `~/agent-sync/sync-vlan-20/docker-compose.yml` |
| `agent-sync/sync-vlan-30/docker-compose.yml` | `~/agent-sync/sync-vlan-30/docker-compose.yml` |
| `creation_vlan.sh` | `~/creation_vlan.sh` : réseaux Docker macvlan, à lancer une fois (relançable) |
| `donnees-vlan-20/docker-compose.yml` | `~/donnees-vlan-20/docker-compose.yml` |
| `donnees-vlan-30/docker-compose.yml` | `~/donnees-vlan-30/docker-compose.yml` |
| `registre/docker-compose.yml` | `~/registre/docker-compose.yml` |
| `scada/docker-compose.yml` | `~/scada/docker-compose.yml` |

Données **amorcées** (déposées seulement si absentes, jamais écrasées) :
- `~/scada/appdata/settings.js` depuis `configurations/conteneurs/scada/donnees/settings.js`
- `~/scada/appdata/mysettings.json` depuis `configurations/conteneurs/scada/donnees/mysettings.json`
- `~/scada/appdata/project.fuxap.db` depuis `configurations/conteneurs/scada/donnees/project.fuxap.db`

## Hors NetBox (à faire ou vérifier à la main)

- Clé SSH du poste d'administration dans `~/.ssh/authorized_keys` ; compte et nom d'hôte = `pi51`.
- Docker installé (`configurations/machines/installation_docker.sh`), mises à jour automatiques désactivées (`configurations/machines/apt/`).
- Images dans `~/images` (`configurations/images/`, chargées par `docker load` ou par l'agent HA).
- `~/.ssh/id_rsa` : clé privée de synchronisation, montée en lecture seule par `sync-vlan-20`, `sync-vlan-30`.
- `~/donnees-vlan-20/.env` : `FTP_PASS=…` (secret, droits 600, jamais versionné).
- `~/donnees-vlan-30/.env` : `FTP_PASS=…` (secret, droits 600, jamais versionné).
