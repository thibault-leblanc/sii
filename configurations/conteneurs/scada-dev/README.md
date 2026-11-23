# FUXA de développement (`scada-dev/`)

Instance FUXA **du poste d'administration**, pour des essais (Docker Desktop, http://localhost:1881). **Ce n'est
pas le SCADA de la plateforme** : celui-ci est [`../scada/`](../scada/README.md), sur pi51 en 192.168.30.10.

| Fichier | Contenu |
|---|---|
| `Dockerfile` | FUXA (image `latest`, non figée) + pilotes OPC-UA et Modbus. |
| `docker-compose.yml` | Conteneur `scada-dev`, port 1881 du poste, données dans `fuxa_appdata/`. |
| `fuxa_appdata/` | Données d'exécution de l'instance (projet, alarmes, utilisateurs…), voir son README. |
| `projet.json`, `projet.json.old`, `vue.json` | Anciens exports de projet et de vue (« Distribution parallèle »), historiques. |

Le projet de cette instance a servi de **référence initiale** au SCADA de la plateforme (copié le 2026-11-23 dans
`../scada/donnees/`). Arrêtée depuis (`docker stop scada-dev`), conservée pour des essais :
`docker start scada-dev`. Elle joint l'automate par le pare-feu (192.168.30.20:4840).
