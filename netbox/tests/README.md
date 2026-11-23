# Tests de l'outillage (`netbox/tests/`)

Tests hors ligne (sans NetBox ni les Pi) : `python -m unittest discover -s tests` depuis `netbox/`.

| Classe | Vérifie |
|---|---|
| `TestModele` | Validation (IP en double, VLAN ou client inconnu), ports, normalisation et comparaison. |
| `TestGeneration` | Fichiers générés : netplan, compose (automate, agent HA, FTP sans secret), noms de projet Compose, `config_cluster.json`, macvlan, services par cluster, vidage du dossier de sortie, topologie, matrice de flux. Valeurs de référence relevées sur la plateforme (derive.py : 0 écart). |
| `TestDerive` | Contrôle de dérive : nœud conforme sans écart ; conteneur oublié, mauvaise IP, mauvais dossier, réseau macvlan différent détectés ; VIP sur le maître acceptée. |
| `TestIaac` | Synchronisation de `iaac/infrastructure.json` : structure lue par l'interface, stabilité, ajouts manuels conservés, objets supprimés retirés. |

Lancés aussi par `synchro.py` et par le garde-fou de commit. Quand le modèle change volontairement (nouvelle
valeur dans NetBox), mettre à jour la valeur attendue du test concerné dans le même commit.
