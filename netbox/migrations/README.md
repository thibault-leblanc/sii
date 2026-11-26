# Migrations NetBox (`netbox/migrations/`)

Les **changements structurants** de NetBox se font par un script daté plutôt qu'à la main dans l'interface :
le changement est relu, versionné, rejouable (sur une instance reconstruite) et tracé.

Règles d'un script de migration :
- nom `AAAA-MM-JJ_sujet.py`, docstring qui explique le contenu et la raison ;
- **relançable sans effet de bord** (idempotent : un 2e passage ne crée ni ne modifie rien) ;
- s'appuie sur `outils/importer.py` (`connecter`, `Importeur.assurer`) ;
- après exécution : `python netbox/outils/synchro.py`, puis une ligne dans `documentation/journal_exploitation.md`.

| Migration | Contenu |
|---|---|
| `2026-11-23_conduite_scada.py` | Champ `clusters` (plusieurs clusters par nœud), cluster `conduite`, poste d'administration côté WAN, service `scada` (192.168.30.10), passerelle VLAN30 et configurations versionnées de l'automate et du simulateur. |
| `2026-11-26_cablage_commutateur.py` | Câblage confirmé par l'administrateur : port 5 en trunk 10/20/30 câblé à pi51, port 2 (vide) retiré. |

Les changements ponctuels (une description, une IP) peuvent se faire dans l'interface de NetBox, suivis de
`synchro.py`.
