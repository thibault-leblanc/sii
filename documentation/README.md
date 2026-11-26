# Documentation

| Document | Contenu | Statut |
|---|---|---|
| [architecture_reference.md](architecture_reference.md) | **Architecture de référence** : principes, niveaux ISA-95, zones et conduits, modèle type de déploiement (classes, fiche de brique, cycle de vie), décisions, écarts connus (§7). | Vivant : §7 à tenir à jour |
| [modop_chaine_livraison.md](modop_chaine_livraison.md) | **Mode opératoire du chantier en cours** : chaîne de livraison locale (registre, images versionnées, dépôt, Ansible, services locaux, coupure d'internet), lots 0 à F et S, non-régression, procédure de déploiement HA. | En cours |
| [dependances_internet.md](dependances_internet.md) | **Registre des dépendances à internet** : nœud, usage, voie, remplacement prévu. | Vivant : à tenir à jour |
| [journal_exploitation.md](journal_exploitation.md) | **Toutes les interventions** sur la plateforme : date, nœud, action, raison, résultat, incidents. | Vivant : à compléter à chaque intervention |
| [audit_fonctionnel.md](audit_fonctionnel.md) | Audit fonctionnel (2026-11-14), plan d'action, et suivi des corrections (§10). | Vivant : §10 mis à jour à chaque correction |
| [specifications_fonctionnelles_rincage.pdf](specifications_fonctionnelles_rincage.pdf) | Procédé de rinçage : physique, logique de l'automate, sécurités, échanges Modbus et OPC-UA. | Référence |
| [recapitulatif_procede_api.pdf](recapitulatif_procede_api.pdf) | Synthèse du procédé et de l'automate. Écart connu : seuil de pH 5,5 (contre 5,0 ailleurs, audit P5). | Référence |
| [IHM_SCADA_Specification.pdf](IHM_SCADA_Specification.pdf) | Spécification de l'IHM de conduite (FUXA). | Référence |
| [archi_plateforme.drawio](archi_plateforme.drawio) | Schéma d'architecture : pages **Physique (réel)**, **Logique (réel)** et **Cible**. Source et date sur chaque page ; NetBox reste la référence. | À jour au 2026-11-26 (lot S) |

Où se trouve le reste :
- l'état voulu de l'infrastructure : NetBox, exporté dans [`netbox/donnees/sii.yaml`](../netbox/donnees/sii.yaml) ;
- l'exploitation (bascules, réinstallation, publication) : [`netbox/README.md`](../netbox/README.md) ;
- les règles de travail des agents Claude Code : [`CLAUDE.md`](../CLAUDE.md) (racine du dépôt) ;
- le fonctionnement de chaque brique : le `README.md` de son dossier sous [`configurations/`](../configurations/README.md).
