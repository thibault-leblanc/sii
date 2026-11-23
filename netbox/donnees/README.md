# Modèle exporté (`netbox/donnees/`)

`sii.yaml` est l'**export de NetBox** : la copie versionnée, lisible et comparable (`git diff`) de l'état voulu
de la plateforme. **On ne l'édite pas à la main** : on modifie NetBox, puis `python netbox/outils/synchro.py`.

| Section | Contenu |
|---|---|
| `a_verifier` | Points non tranchés (câblage, pare-feu…). Seule section propre au fichier : elle ne vit pas dans NetBox et est conservée par l'export. |
| `site`, `dns` | Site NetBox et serveurs DNS (contexte de configuration `sii-reseau`). |
| `vlans` | VLAN 10/20/30 : préfixe, plage macvlan. |
| `roles`, `plateformes`, `types`, `clusters` | Catalogue : rôles d'équipement, OS, modèles, clusters (`fonctionnel`, `infra`, `conduite`). |
| `equipements` | Nœuds et matériel réseau : clusters, interfaces (VLAN, IP, câbles), ports exposés et clients autorisés. |
| `vrrp` | Groupe de haute disponibilité `coeur-sii` : VIP, VRID, priorités. |
| `services` | Conteneurs : cluster, IP, ports, `compose`, `passerelle`, `fichiers`, `amorcage`, `ha`. |

Historique : créé le 2026-11-19 depuis l'ancien `iaac/infrastructure.json` (corrigé des constats I1 à I9 de
l'audit), puis chargé dans NetBox ; depuis le 2026-11-22, c'est un export de NetBox.
