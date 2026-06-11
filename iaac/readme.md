# 🏗️ IaaC - SII Plateforme

Ce répertoire contient le socle **Infrastructure as Code (IaaC)** de la plateforme de Système d'Information Industriel (SII). 

L'objectif de ce module est de maintenir une **Source Unique de Vérité (Single Source of Truth)** pour l'ensemble du SII c'est à dire : des équipements physiques (pare-feux, commutateurs, Raspberry Pi) et des charges de travail logiques (conteneurs Docker, simulation physique, API, applications, configurations, ...) mais aussi MCO/MCS, sécurité, ...

## 📂 Architecture du dossier

* `schema.json` : La structure centrale. Il décrit la structure de la topologie.
* `infrastructure.json` : Le manifeste central. Il décrit la topologie complète (réseaux, équipements, adresses IP, VLANs).
* `index.html` : L'interface web de gestion. Elle permet de générer un graphe de topologie dynamique et d'éditer le manifeste JSON directement depuis un navigateur.

## 🚀 Démarrage de l'Interface Web

1. Ouvrir un terminal dans ce dossier (`/iaac`).
2. Exécuter la commande Python suivante :
   ```bash
   python -m http.server 8000
