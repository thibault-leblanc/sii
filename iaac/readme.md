# 🏗️ IaaC - SII Plateforme

Ce répertoire contient le socle **Infrastructure as Code (IaaC)** de la plateforme de Système d'Information Industriel (SII). 

L'objectif de ce module est de maintenir une **Source Unique de Vérité (Single Source of Truth)** pour l'ensemble du SII, c'est-à-dire : des équipements physiques (pare-feux, commutateurs, clusters de Raspberry Pi) et des charges de travail logiques (conteneurs Docker, simulation physique de procédés, API, applications, configurations), mais aussi le MCO/MCS, la sécurité, etc.

Désormais, cet outil ne se contente plus de documenter : il intègre un moteur d'**auto-provisioning** capable de générer à la volée les scripts de configuration (réseau, arborescence, OS) pour initialiser les machines directement depuis le manifeste central.

## ✨ Fonctionnalités Principales

* 👁️ **Graphe de Topologie Dynamique :** Visualisation interactive des équipements, réseaux L2/L3 (VLANs), trunks et hébergements.
* 📝 **Édition Pilotée par les Données (Data-Driven) :** Interface de modification dynamique générée automatiquement depuis un `schema.json` restrictif.
* ⚙️ **Moteur de Provisioning (Templating) :** Génération de scripts bash d'initialisation (`.sh`) contextuels (ex: calcul automatique des configurations Netplan et des arborescences pour Ubuntu Server).
* 📋 **Calcul d'Impact Périphérique :** Génération de checklists administrateur pour la configuration des ports de commutateurs et pare-feux liés aux équipements.
* 🚀 **Serveur "Zéro Dépendance" :** Un backend Python léger et autonome, ne nécessitant aucune installation de paquet externe (pas de `pip install`).

## 📂 Architecture du projet

```text
/iaac
├── serveur.py                   # Serveur local Python (API REST & Serveur Web)
├── infrastructure.json          # Le manifeste central (La source de vérité)
├── schema.json                  # Le dictionnaire de règles et types de l'infrastructure
└── templates/
    ├── index.html               # L'interface web de gestion (SPA)
    └── provisioning/
        └── ubuntu_init.template.sh  # Modèle de script d'initialisation (OS Ubuntu)
```

## 🚀 Démarrage de l'Interface Web

Le projet inclut un micro-serveur Python natif pour gérer la lecture/écriture sécurisée des fichiers JSON locaux et le moteur de templating.

1. Ouvrir un terminal dans ce dossier (`/iaac`).
2. Exécuter la commande suivante (nécessite Python 3) :
   ```bash
   python serveur.py
   ```
3. Ouvrir un navigateur web et se rendre à l'adresse indiquée dans le terminal (par défaut : `http://127.0.0.1:5000`).

## 🛠️ Utilisation

L'interface web se divise en 3 onglets principaux :
1. **Topologie :** Cliquez sur un nœud (machine physique ou logique) pour ouvrir le panneau latéral. Depuis ce panneau, vous pouvez modifier ses propriétés, générer son script de provisioning (`⚙️ Générer Script de Config`), ou le supprimer.
2. **Données :** Accès direct au code source de `infrastructure.json` avec validation d'erreurs en temps réel et outils de formatage interactifs.
3. **Schéma :** Modification des règles de l'infrastructure (ajout de nouveaux matériels supportés, définition de nouvelles listes déroulantes, etc.).

Les modifications apportées dans l'interface sont sauvegardées en temps réel sur le disque dur local.
