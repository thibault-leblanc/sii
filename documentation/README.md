# Documentation

| Document | Contenu | Statut |
|---|---|---|
| [journal_exploitation.md](journal_exploitation.md) | **Toutes les interventions** sur la plateforme : date, nœud, action, raison, résultat, incidents. | Vivant : à compléter à chaque intervention |
| [audit_fonctionnel.md](audit_fonctionnel.md) | Audit fonctionnel (2026-11-14), plan d'action, et suivi des corrections (§10). | Vivant : §10 mis à jour à chaque correction |
| [specifications_fonctionnelles_rincage.pdf](specifications_fonctionnelles_rincage.pdf) | Procédé de rinçage : physique, logique de l'automate, sécurités, échanges Modbus et OPC-UA. | Référence |
| [recapitulatif_procede_api.pdf](recapitulatif_procede_api.pdf) | Synthèse du procédé et de l'automate. Écart connu : seuil de pH 5,5 (contre 5,0 ailleurs, audit P5). | Référence |
| [IHM_SCADA_Specification.pdf](IHM_SCADA_Specification.pdf) | Spécification de l'IHM de conduite (FUXA). | Référence |
| [archi_plateforme.drawio](archi_plateforme.drawio) | Schéma d'architecture (pages Logique et Physique). | **Périmé** sur le câblage et le placement du SCADA (audit S1 à S6) : la vue technique de référence est NetBox (`netbox/genere/topologie.html`, interface `iaac/`). |

Où se trouve le reste :
- l'état voulu de l'infrastructure : NetBox, exporté dans [`netbox/donnees/sii.yaml`](../netbox/donnees/sii.yaml) ;
- l'exploitation (bascules, réinstallation, publication) : [`netbox/README.md`](../netbox/README.md) ;
- le fonctionnement de chaque brique : le `README.md` de son dossier sous [`configurations/`](../configurations/README.md).
