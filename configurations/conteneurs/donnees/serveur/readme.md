# 📥 Serveur FTP (ingestion des données)

Serveur FTP léger (`vsftpd`, Alpine), exposé sur un VLAN par macvlan, pour que les équipements y déposent
leurs fichiers.

## Fonctionnement

* Utilisateur créé au démarrage depuis `FTP_USER` et `FTP_PASS`.
* Fichiers reçus dans le volume `/partage`, la racine FTP du VLAN sur l'hôte.
* Ports passifs 21000-21010.

## Déploiement

Le compose est généré depuis NetBox (`netbox/README.md`). Le mot de passe est lu dans le fichier `.env` du
dossier du service sur `pi51` (`FTP_PASS=…`, droits 600) : il n'est stocké ni dans NetBox ni dans git.

Construction de l'image :

```bash
sh configurations/construire_images.sh serveur-ftp
```

⚠️ La racine FTP (`~/donnees/vlanXX`) n'est pas le dossier synchronisé (`~/donnees/vlanXX/donnees`) :
un fichier déposé à la racine n'est pas répliqué (audit D8).
