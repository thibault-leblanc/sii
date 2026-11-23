# Script d'initialisation d'un nœud (`iaac/templates/provisioning/`)

`ubuntu_init.template.sh` est rempli par `iaac/serveur.py` (bouton « Générer Script de Config » de l'interface)
pour le nœud choisi :
- `{{NODE_ID}}` : nom d'hôte ;
- `{{NETPLAN_YAML}}` : netplan **produit par le générateur NetBox** (`netbox/outils/generer.py`), identique à
  `configurations/machines/<nœud>/99-<nœud>-netplan.yaml` ;
- `{{MKDIR_CMDS}}` : création des dossiers du nœud (contexte NetBox : racine des projets, données).

Le script s'exécute en root sur le nœud. Il fait `netplan apply` : un netplan faux coupe l'accès au nœud ;
préférer `netplan try`, qui revient en arrière seul. Procédure complète de (ré)installation : `netbox/README.md`.
