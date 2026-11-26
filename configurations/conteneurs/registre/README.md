# Registre d'images (`registre`)

Registre Docker local sur pi51 : les images de la plateforme y sont poussées depuis le poste d'administration et
tirées par les nœuds, à la place des archives `.tar`. Image tierce, rien à construire : ce dossier ne porte que la
fiche. Le compose est généré depuis NetBox (`configurations/machines/pi51/registre/`).

## Fiche de brique

- Rôle : stocker et servir les images versionnées de la plateforme.
- Niveau ISA-95 / zone : transverse (socle) / administration, VLAN10.
- Classe de déploiement : B (persistant).
- Service NetBox / cluster : `registre` / `infra` (pi51).
- Image et origine : `registry:3.1.2`, tierce (Docker Hub, projet CNCF Distribution), licence Apache 2.0.
- Flux entrants et sortants : tcp/5000 depuis le poste d'administration (envoi), pi31 et pi32 (tirage), déclarés
  dans NetBox. Publié sur l'hôte en `192.168.10.12:5000`, sans IP macvlan.
- Données produites et consommées : images, dans `~/registre/data` sur pi51.
- Données persistantes, sauvegarde, restauration : `~/registre/data` ; sauvegarde hors de pi51 à mettre en place
  (lot D). Une archive `.tar` des images de base est gardée hors git pour reconstruire pi51 (lot B).
- Dépendances, et comportement si elles manquent : aucune en exécution. Registre arrêté : les conteneurs en marche
  ne sont pas touchés ; seuls les tirages échouent.
- Santé : `curl http://192.168.10.12:5000/v2/_catalog` répond.
- Test avant publication / contrôle après déploiement : catalogue joignable depuis le poste, pi31 et pi32 ; une
  image de test arm64 poussée depuis le poste est tirée par pi32 ; `derive.py` 0 écart.
- Retour arrière : retirer le service par migration, `docker compose down` dans `~/registre`, restaurer
  `/etc/docker/daemon.json` sur les nœuds puis `systemctl reload docker`.
- Écarts à l'architecture de référence : HTTP sans authentification (E7, assumé jusqu'à la GIA) ; nœud
  d'infrastructure unique (E8).
