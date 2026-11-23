# Données de l'instance FUXA de développement (`scada-dev/fuxa_appdata/`)

Monté dans le conteneur `scada-dev` (`/usr/src/app/FUXA/server/_appdata`). FUXA y écrit en permanence :
`project.fuxap.db` (projet), `alarms.fuxap.db`, `users.fuxap.db`, `scheduler.db`, `apikeys.fuxap.db`,
`settings.js`, `mysettings.json`, `_upload_files/`.

Ces fichiers sont des **données d'exécution** : le `.gitignore` les ignore (`*/fuxa_appdata/*`), mais certains
avaient été suivis avant cette règle et apparaissent donc modifiés après chaque essai. Ne pas les commiter
par habitude. Le projet de référence de la plateforme est dans `../../scada/donnees/`.
