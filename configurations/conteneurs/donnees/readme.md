# 🗄️ Gestion des données (stockage et réplication)

Ce répertoire contient les **images** des services de données, hébergés sur le nœud central `pi51` (cluster `infra`) :

1. **[Serveur FTP](./serveur/)** : ingestion des fichiers déposés par les équipements, un serveur par VLAN (20, 30).
2. **[Agent de synchronisation](./agent-sync/)** : réplication unidirectionnelle, toutes les 60 s, du dossier de chaque
   VLAN vers les nœuds du cluster `fonctionnel` (`pi31`, `pi32`).

Chaque VLAN a son couple FTP + agent : un agent ne voit que les données de son VLAN, montées en lecture seule.

## Déploiement

Le déploiement **ne se fait plus à la main** : adresses IP, réseaux macvlan, dossiers et variables sont décrits
dans NetBox, et les `docker-compose.yml` sont générés dans `configurations/machines/pi51/` (`netbox/outils/generer.py`).
Voir `netbox/README.md`. Les images se construisent avec `sh configurations/construire_images.sh`.

| Service | Dossier sur pi51 | Données |
|---|---|---|
| `donnees-vlan-20` | `~/donnees-vlan-20` | racine FTP `~/donnees/vlan20` |
| `donnees-vlan-30` | `~/donnees-vlan-30` | racine FTP `~/donnees/vlan30` |
| `sync-vlan-20` | `~/agent-sync/sync-vlan-20` | `~/donnees/vlan20/donnees` → `~/donnees/vlan20/donnees` des nœuds |
| `sync-vlan-30` | `~/agent-sync/sync-vlan-30` | `~/donnees/vlan30/donnees` → `~/donnees/vlan30/donnees` des nœuds |

Le mot de passe FTP n'est ni dans le repo ni dans NetBox : il est lu dans le fichier `.env` (droits 600) du
dossier de chaque serveur FTP.
