# Projet FUXA de référence (`scada/donnees/`)

Données FUXA **amorcées** sur pi51 (`~/scada/appdata`) : déposées seulement si elles sont absentes, jamais
écrasées ensuite (déclarées dans NetBox, service `scada`, champ `amorcage`).

| Fichier | Contenu |
|---|---|
| `project.fuxap.db` | Projet (SQLite) : vues, variables, équipements. `OPCUA_RINCAGE` → 192.168.30.20:4840 et ses 16 variables ; `MBTCP_RINCAGE`, accès Modbus direct au simulateur (audit P6). |
| `settings.js` | Réglages du serveur FUXA (port 1881, origines autorisées `http://192.168.*`…). |
| `mysettings.json` | Réglages de l'IHM (langue, authentification **désactivée**). |

Mettre à jour la référence après une modification dans l'éditeur FUXA : voir [`../README.md`](../README.md).
Les variables de `OPCUA_RINCAGE` sont lues par `tests/plateforme/verifier_chaine_scada.py`.
