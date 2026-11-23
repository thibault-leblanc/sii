# Interface web de l'IaC (`iaac/templates/`)

| Fichier | Rôle |
|---|---|
| `index.html` | Application d'une page servie par `iaac/serveur.py` : graphe de topologie (vis-network : équipements, VLAN, services, câbles, clusters), éditeurs de `infrastructure.json` et `schema.json` (JSONEditor), fiche de détail pilotée par le schéma, demande du script d'initialisation d'un nœud. |
| [`provisioning/`](provisioning/README.md) | Modèle du script d'initialisation d'un nœud Ubuntu. |

Les bibliothèques (vis-network, JSONEditor) sont chargées depuis un CDN : le poste doit avoir accès à Internet.
