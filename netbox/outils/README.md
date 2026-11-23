# Outillage IaC (`netbox/outils/`)

Scripts Python (pas de dépendance hormis `pynetbox` et `pyyaml`, voir `requirements.txt`) qui relient NetBox, le
repo et les nœuds. Ils se lancent depuis `netbox/` ou la racine du repo.

| Script | Rôle | Commande type |
|---|---|---|
| `synchro.py` | **Commande unique** : export NetBox → `sii.yaml` → `iaac/infrastructure.json` → génération → tests. `--verifier` ne fait que contrôler (garde-fou de commit). | `python netbox/outils/synchro.py` |
| `modele.py` | Chargement, **validation** (IP en double, VLAN, câbles, clients, fichiers référencés…), normalisation et comparaison du modèle. Bibliothèque commune aux autres scripts. | `python outils/modele.py` |
| `exporter.py` | NetBox → format `sii.yaml`. `--comparer` : écarts entre un fichier et NetBox. | `python outils/exporter.py -o donnees/sii.yaml` |
| `importer.py` | `sii.yaml` → NetBox **vide** (reconstruction). Ne pas lancer sur l'instance en service. | `python outils/importer.py` |
| `vers_iaac.py` | Synchronise `iaac/infrastructure.json` (champs NetBox réécrits, ajouts manuels conservés). | `python outils/vers_iaac.py` |
| `generer.py` | Modèle → `configurations/machines/<noeud>/` (versionné : netplan, réseaux macvlan, compose, `config_cluster.json`, configurations, fiche du nœud) et `genere/` (hors git : amorçage, matrice de flux, topologie, `publier.sh`). | `python outils/generer.py` |
| `collecte.sh` | Relève l'état réel d'un nœud (réseau, conteneurs, réseaux Docker) en JSON. Lecture seule. | `ssh pi31@192.168.10.10 sh -s < outils/collecte.sh > collecte/pi31.json` |
| `derive.py` | Compare les relevés au modèle : un écart par ligne, code 1 s'il en reste. | `python outils/derive.py collecte/` |

Accès à NetBox : variables `NETBOX_URL` et `NETBOX_TOKEN` (jeton v2 `nbt_…`, pynetbox ≥ 7.9).

Principes : NetBox fait foi ; tout ce qui est déployé sort de `generer.py` ; un fichier périmé (dossier de nœud ou `genere/`) ne
peut pas être publié (le dossier est vidé à chaque génération, s'il porte la marque `.genere-par-netbox`).
Tests : `../tests/`.
