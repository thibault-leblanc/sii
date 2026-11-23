# Scripts de l'agent HA (`cluster/scripts/`)

Copiés dans l'image (`/usr/local/bin/`, fins de ligne forcées en LF). Fonctionnement d'ensemble et raisons de
chaque mécanisme : [`../README.md`](../README.md).

| Script | Appelé par | Rôle |
|---|---|---|
| `entrypoint.sh` | Docker (démarrage) | Lit `/config/config_cluster.json`, écrit `keepalived.conf` (FAULT sur sonde en échec, `nopreempt`, `notify_stop`), écrit les listes de services et d'IP, lance `auto_loader.sh` et `garde_fou.sh`, puis keepalived. |
| `check_health.sh` | keepalived (toutes les 10 s) | Sain si chaque service piloté tourne ; toujours sain sur un BACKUP (`/tmp/force_backup`). |
| `action.sh` | keepalived (MASTER, BACKUP, FAULT, STOP) | Démarre ou arrête les services. Sérialisé (verrou) ; contrôle ARP des IP avant tout démarrage. |
| `garde_fou.sh` | `entrypoint.sh` (boucle) | Sans VIP, arrête tout service piloté en marche (après 2 constats, ~20 s). |
| `auto_loader.sh` | `entrypoint.sh` (boucle) | Charge les `.tar` de `~/images` nouveaux ou plus récents (marques dans `/etat`, soit `~/.agent-ha` sur l'hôte). |

Fichiers de travail dans le conteneur : `/etc/keepalived/{services,adresses,vip,iface}`, `/tmp/etat_voulu`,
`/tmp/force_backup`, `/tmp/demarrage`. Journal : `docker logs ha-cluster` (lignes « agent HA : … »).
