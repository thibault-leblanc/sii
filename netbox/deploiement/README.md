# Déploiement de NetBox (`netbox/deploiement/`)

NetBox tourne avec [netbox-docker](https://github.com/netbox-community/netbox-docker), **cloné à part** du repo
(il contient des secrets : mots de passe de la base, clé secrète) : `D:\Documents\Cyber\netbox-docker`.

`docker-compose.override.yml` est la seule personnalisation, à copier dans ce clone :
- port `8000` sur le poste ;
- délai de démarrage de 900 s (le premier démarrage crée toutes les tables, plus de 5 minutes sur le poste).

Aucun identifiant dans ce fichier : l'administrateur est créé avec `manage.py createsuperuser`, le jeton d'API
dans le profil. Installation pas à pas : `netbox/README.md`, « Démarrer NetBox ». Les données de NetBox vivent dans
des volumes Docker : sauvegarde par `pg_dump` (conteneur `postgres`), et l'export `sii.yaml` dans git.
Si NetBox ne répond plus (arrêt de Docker Desktop) : `cd netbox-docker && docker compose up -d`.
