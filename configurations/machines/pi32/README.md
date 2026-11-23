# pi32

> Dossier **généré** par `netbox/outils/generer.py` depuis NetBox : ne pas le modifier à la main.
> Modifier NetBox, puis `python netbox/outils/synchro.py` ; publier avec `sh netbox/genere/publier.sh`.

| | |
|---|---|
| Rôle | Nœud fonctionnel : Hôte de calcul Edge (relais / passif) |
| Matériel | Raspberry Pi 3 Model B |
| Système | Ubuntu Server 26.04 |
| Clusters | fonctionnel |
| Accès | `ssh pi32@192.168.10.11` |
| Haute disponibilité | groupe VRRP `coeur-sii` (VRID 51, VIP 192.168.10.251/24), priorité 90 |

## Réseau

| Interface | VLAN | IP | Câble |
|---|---|---|---|
| `eth0` | trunk 10, 20, 30 |  | commutateur/port4 |
| `eth0.10` | 10 | 192.168.10.11/24 |  |
| `eth0.20` | 20 |  |  |
| `eth0.30` | 30 |  |  |

## Services

| Service | Dossier | IP | Démarrage | Image |
|---|---|---|---|---|
| `api-rincage` (fonctionnel) | `~/api/rincage` | 192.168.20.20, 192.168.30.20 | agent HA, sur le maître seulement | `api-rincage-image:latest` |
| `ha-cluster` (fonctionnel) | `~/ha-cluster` |  | Docker, réseau de l'hôte | `agent-ha:latest` |
| `sim-rincage` (fonctionnel) | `~/simulation/rincage` | 192.168.20.10 | agent HA, sur le maître seulement | `simu-rincage-image:latest` |

## Fichiers de ce dossier

| Fichier | Destination sur le nœud |
|---|---|
| `99-pi32-netplan.yaml` | `/etc/netplan/` : `sudo install -m 600 ~/99-pi32-netplan.yaml /etc/netplan/ && sudo netplan try` |
| `api/rincage/config_api.json` | `~/api/rincage/config_api.json` |
| `api/rincage/docker-compose.yml` | `~/api/rincage/docker-compose.yml` |
| `config_cluster.json` | `~/config_cluster.json` : lu par l'agent HA |
| `creation_vlan.sh` | `~/creation_vlan.sh` : réseaux Docker macvlan, à lancer une fois (relançable) |
| `ha-cluster/docker-compose.yml` | `~/ha-cluster/docker-compose.yml` |
| `simulation/rincage/config_simu.json` | `~/simulation/rincage/config_simu.json` |
| `simulation/rincage/docker-compose.yml` | `~/simulation/rincage/docker-compose.yml` |

## Hors NetBox (à faire ou vérifier à la main)

- Clé SSH du poste d'administration dans `~/.ssh/authorized_keys` ; compte et nom d'hôte = `pi32`.
- Docker installé (`configurations/machines/installation_docker.sh`), mises à jour automatiques désactivées (`configurations/machines/apt/`).
- Images dans `~/images` (`configurations/images/`, chargées par `docker load` ou par l'agent HA).
- Clé publique de `pi51` (`~/.ssh/id_rsa.pub`, utilisée par `sync-vlan-20`, `sync-vlan-30`) dans `~/.ssh/authorized_keys`.
- `api-rincage` : conteneur créé d'avance (`cd ~/api/rincage && docker compose create`), jamais `up` : c'est l'agent HA qui le démarre.
- `sim-rincage` : conteneur créé d'avance (`cd ~/simulation/rincage && docker compose create`), jamais `up` : c'est l'agent HA qui le démarre.
