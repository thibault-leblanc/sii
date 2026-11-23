# 🏗️ IaC historique de la plateforme (`iaac/`)

Modèle JSON de la plateforme et **interface web interactive** (graphe de topologie, édition, script
d'initialisation d'un nœud). Depuis novembre 2026, **NetBox est la source de vérité** : ce dossier en est une
**copie synchronisée et enrichissable**, conservée tant que le modèle définitif d'IaC n'est pas choisi.

## Synchronisation avec NetBox

```text
NetBox ──export──► netbox/donnees/sii.yaml ──vers_iaac.py──► iaac/infrastructure.json ◄── vos ajouts
```

- Commande : `python netbox/outils/synchro.py` (fait tout : export, IaC, génération, tests).
- Règles de fusion (`netbox/outils/vers_iaac.py`) :
  - **un champ qui vient de NetBox est réécrit** à chaque synchronisation : le modifier ici ne sert à rien,
    il faut le modifier dans NetBox ;
  - **un champ ou une section ajoutés à la main sont conservés** (notes, informations que NetBox ne porte pas) ;
  - un objet supprimé de NetBox disparaît d'ici.
- Le garde-fou de commit (`.githooks/pre-commit`) refuse un commit si ce fichier n'est pas à jour.

## Contenu de `infrastructure.json`

| Section | Contenu |
|---|---|
| `metadonnes` | Origine (NetBox), date de dernière modification. |
| `reseaux_globaux` | VLAN : préfixe, passerelle (IP du pare-feu), plage macvlan. |
| `clusters` | `fonctionnel`, `infra`, `conduite` et leurs membres. |
| `ressources_physiques` | Équipements : type, rôle, modèle, IP de gestion, clusters, interfaces (VLAN, câbles), ports exposés. |
| `ressources_logiques` | Services (conteneurs) : cluster, nœuds hôtes, HA, IP, ports, compose, fichiers de configuration et d'amorçage. |
| `vrrp` | Groupe de haute disponibilité : VIP, VRID, priorités. |
| `flux` | Matrice des flux autorisés (qui joint quoi, et si le pare-feu est traversé). |

## Interface web

```sh
cd iaac && python serveur.py      # http://127.0.0.1:5000
```

- **Topologie** : graphe interactif (équipements, VLAN, services, câbles, clusters).
- **Données** / **Schéma** : édition de `infrastructure.json` et `schema.json`. Rappel : les champs NetBox
  modifiés ici seront réécrits à la prochaine synchronisation.
- **Script d'initialisation** d'un nœud : produit par le générateur NetBox (même netplan que `netbox/genere/`).

Fichiers : `serveur.py` (serveur local sans dépendance hormis l'outillage `netbox/outils`), `schema.json`,
`templates/index.html`, `templates/provisioning/ubuntu_init.template.sh`. `sav/` : anciennes versions (archives).
