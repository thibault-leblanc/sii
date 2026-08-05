# 🔄 Agent de Synchronisation Rsync

Ce conteneur a pour rôle de répliquer en continu les données depuis le nœud de stockage central vers les nœuds Edge (`pi31`, `pi32`). Basé sur Alpine Linux, il utilise `rsync` au travers de tunnels SSH.

## ⚙️ Fonctionnement

* **Boucle infinie :** Le conteneur exécute un script (`sync.sh`) qui déclenche une synchronisation toutes les 60 secondes.
* **Incrémental et Sécurisé :** Les transferts se font de manière incrémentale. Le volume de données source est monté en lecture seule (`:ro`) pour éviter toute altération accidentelle sur le serveur central.
* **Ciblage dynamique :** Le dossier de destination sur les nœuds Edge est déterminé par la variable d'environnement `$VLAN_CIBLE`. Cela permet d'utiliser la même image Docker pour synchroniser des données vers différents répertoires de VLAN sans conflit de suppression (Split-Brain).

## 🚀 Utilisation et Déploiement

### 1. Construction de l'image de base

```bash
docker build -t agent-sync:latest .
```

### 2. Déploiement dynamique

Le script `deploiement_sync.sh` génère l'infrastructure as code du conteneur en injectant la variable de ciblage et en gérant les clés SSH requises pour l'authentification automatique.

**Syntaxe :**
```bash
./deploiement_sync.sh <NUMERO_VLAN> <IP_CONTENEUR> <NOM_MACVLAN>
```

**Exemple de déploiement pour les données du VLAN 20 :**
```bash
./deploiement_sync.sh 20 192.168.20.31 vlan20
```

Le script montera automatiquement la clé SSH de l'hôte (`/home/pi51/.ssh/id_rsa`) ainsi que le dossier de données source correspondant (`/home/pi51/donnees/vlan20/donnees`).