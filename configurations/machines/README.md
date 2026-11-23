# Nœuds de la plateforme (`configurations/machines/`)

| Chemin | Nature | Contenu |
|---|---|---|
| [`pi31/`](pi31/README.md), [`pi32/`](pi32/README.md), [`pi51/`](pi51/README.md) | **Généré** depuis NetBox | Tout ce qui est déployé sur le nœud (netplan, réseaux macvlan, docker-compose, `config_cluster.json`, configurations des applications) et sa **fiche** (`README.md` : rôle, réseau, services, destination de chaque fichier, actions manuelles). |
| `installation_docker.sh` | Écrit à la main | Installe Docker Engine et Compose, ajoute l'utilisateur au groupe `docker`. |
| [`apt/`](apt/README.md) | Écrit à la main | Désactivation des mises à jour automatiques (elles redémarraient Docker, donc le procédé). |

## Dossiers des nœuds

Ils sont **versionnés** : `git log -p configurations/machines/pi51/` montre l'historique exact de ce qui a été
déployé, et `git diff` l'effet de chaque changement fait dans NetBox. Ils ne s'éditent **jamais** à la main :

1. modifier NetBox, puis `python netbox/outils/synchro.py` (régénère les dossiers) ;
2. relire `git diff configurations/machines/` ;
3. publier : `sh netbox/genere/publier.sh` (aperçu), puis `--appliquer` ;
4. contrôler : `collecte.sh` puis `derive.py` (0 écart) ; commiter.

Un dossier porte la marque `.genere-par-netbox` : le générateur le vide et le réécrit entièrement (un fichier
retiré de NetBox disparaît). Le garde-fou de commit refuse un dossier qui ne correspond plus à NetBox. Les données
**amorcées** (projet FUXA) ne sont pas ici mais dans `configurations/conteneurs/scada/donnees/`.

## Conventions et préparation de l'hôte

Hôte Ubuntu Server 26.04 arm64 ; compte et nom d'hôte = nom du nœud ; données dans `~/donnees/vlanXX/donnees` ;
images dans `~/images`. Procédure complète de (ré)installation : `netbox/README.md`, « (Ré)installer un nœud ».

Mettre à jour les paquets d'un nœud : décision explicite, **nœud passif d'abord** ; sur le maître, basculer avant
(`docker stop ha-cluster`), mettre à jour, puis relancer l'agent.
