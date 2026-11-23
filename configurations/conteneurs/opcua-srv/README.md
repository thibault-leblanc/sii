# Archive : serveur OPC-UA de test (`opcua-srv/`)

**Non déployé.** Serveur OPC-UA d'essai (asyncua) qui anime quelques variables (ex. une température qui monte)
pour valider la chaîne OPC-UA et un client SCADA avant l'existence de l'automate.

| Fichier | Contenu |
|---|---|
| `opcua_server.py`, `config_opcua.json` | Serveur et variables. |
| `app.py` | Animation des valeurs. |
| `Dockerfile`, `docker-compose.yml` | Conteneur `test-opcua-srv`. |

⚠️ Il utilisait les IP **192.168.20.30 et 192.168.30.30**, aujourd'hui celles des serveurs FTP (audit D11) : ne pas
le relancer tel quel. Variante en script dans `configurations/machines/pi31/` et `pi32/`. Candidat à la suppression.
