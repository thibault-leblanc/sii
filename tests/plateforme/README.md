# Vérifications sur la plateforme allumée (`tests/plateforme/`)

Scripts qui interrogent la vraie plateforme. Ce ne sont pas des tests unitaires : `unittest discover` ne les lance
pas. À lancer depuis le poste d'administration (routes vers les VLAN par le pare-feu, `pymodbus` installé).

| Script | Vérifie |
|---|---|
| `verifier_chaine_scada.py` | Chaîne de conduite : FUXA (API web) → OPC-UA → automate → Modbus → simulateur. Lecture seule par défaut ; `--marche` envoie « Marche » par FUXA et contrôle l'effet directement sur les bobines du simulateur (le procédé reste en marche). |

Complément : la conformité de l'infrastructure se vérifie avec `netbox/outils/collecte.sh` et `derive.py`.
