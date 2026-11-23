# Tests

| Test | Ce qu'il vérifie | Lancement |
|---|---|---|
| `test_procede.py` | **Hors ligne.** Logique de l'automate (repli de sécurité, hystérésis, purge et remplissage, défaut, manuel) et physique du simulateur ; procédé complet couplé sur 4 h simulées. | `python -m unittest discover -s tests` (racine du repo) |
| `../netbox/tests/test_outils.py` | **Hors ligne.** Modèle, génération, synchronisation de l'IaC, contrôle de dérive. | `python -m unittest discover -s tests` (dans `netbox/`) |
| `plateforme/verifier_chaine_scada.py` | **Sur la plateforme allumée.** FUXA → OPC-UA → automate → Modbus → simulateur, avec contrôle indépendant sur les bobines du simulateur. | `python tests/plateforme/verifier_chaine_scada.py [--marche]` |

Les tests hors ligne sont lancés par `python netbox/outils/synchro.py` et par le garde-fou de commit.

Anciens clients de test manuels (non automatisés, conservés) : `client_mb_async.py`, `client_mb_sync.py`
(clients Modbus), `opcua-srv.py` (serveur OPC-UA d'essai).
