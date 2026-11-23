# Archive : premier script d'installation (`configurations/autres/`)

**Non utilisé.** `installation.sh` (≈ 385 lignes) est le tout premier script « tout-en-un » qui configurait un
hôte (VLAN par netplan) puis créait et lançait les conteneurs d'un premier procédé.

Remplacé par :
- la préparation des nœuds : `configurations/machines/` ;
- le réseau et les déploiements, générés depuis NetBox : `netbox/` (`generer.py`, `publier.sh`).

Conservé pour l'historique ; candidat à la suppression (il reste dans l'historique git).
