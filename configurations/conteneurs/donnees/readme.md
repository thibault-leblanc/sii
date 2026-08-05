# 🗄️ Gestion des Données (Stockage & Réplication)

Ce répertoire regroupe les briques d'infrastructure responsables de l'ingestion et de la distribution des données au sein du Système d'Information Industriel (SII). Hébergés sur le nœud central (`pi51`), ces services assurent la liaison entre les équipements de terrain et les nœuds de calcul Edge (`pi31`, `pi32`).

## 🏗️ Architecture

Le flux de données repose sur deux composants complémentaires et découplés :
1. **[Serveur FTP](./serveur-ftp/) :** Gère l'ingestion des fichiers (configurations, logs, relevés) provenant des différents réseaux (VLAN20, VLAN30).
2. **[Agent de Synchronisation](./agent-sync/) :** Assure la réplication incrémentale et unilatérale des données ingérées vers les nœuds de calcul Edge du cluster haute disponibilité (`ha-cluster`).

## 🔄 Principe de fonctionnement

Afin de garantir une stricte ségrégation des réseaux (VLAN), chaque sous-réseau dispose de son propre couple de conteneurs (1 FTP + 1 Agent Sync). 

Les scripts de déploiement permettent de générer à la volée les fichiers `docker-compose.yml` en injectant les bonnes adresses IP (via réseau Macvlan) et les variables d'environnement spécifiques au réseau ciblé.