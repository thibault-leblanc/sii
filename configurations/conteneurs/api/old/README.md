# Archive : premier prototype d'automate (`api/old/`)

**Non déployé.** Prototype d'automate pour un procédé de **cuve chauffée** (niveau, température, vanne de
remplissage, chauffage, pompe de vidange, étapes de grafcet), exposé en OPC-UA.

| Fichier | Contenu |
|---|---|
| `core_api.py` | Mémoire et cycle de l'automate (grafcet). |
| `client_modbus_es.py` | Client Modbus vers le simulateur de cuve. |
| `opcua_srv.py`, `config_opcua_srv.json` | Serveur OPC-UA. |
| `app.py`, `Dockerfile`, `docker-compose.yml` | Lancement. |

Associé au simulateur [`../../sim/old_cuve_pression/`](../../sim/old_cuve_pression/README.md). Remplacé par
l'automate du rinçage ([`../rincage/`](../rincage/README.md)). Candidat à la suppression.
