# Conteneurs (`configurations/conteneurs/`)

Un dossier par image : code, `Dockerfile` (versions figées), `.dockerignore`, configuration de l'application et
`README.md`. Les docker-compose ne sont pas ici : ils sont générés depuis NetBox.

| Dossier | Statut | Contenu |
|---|---|---|
| [`api/rincage/`](api/rincage/README.md) | **En service** | Automate du rinçage (Modbus + OPC-UA) |
| [`sim/rincage/`](sim/rincage/README.md) | **En service** | Simulateur physique (serveur Modbus) |
| [`cluster/`](cluster/README.md) | **En service** | Agent de haute disponibilité |
| [`scada/`](scada/README.md) | **En service** | SCADA FUXA |
| [`donnees/`](donnees/readme.md) | **En service** | Serveur FTP et agent rsync par VLAN |
| [`scada-dev/`](scada-dev/README.md) | Essais | FUXA de développement du poste d'administration |
| [`api/old/`](api/old/README.md), [`sim/old_cuve_pression/`](sim/old_cuve_pression/README.md), [`opcua-srv/`](opcua-srv/README.md) | Archives | Premiers prototypes, non déployés |

Construction : `sh configurations/construire_images.sh [nom]` (arm64, `.tar` dans `configurations/images/`).
