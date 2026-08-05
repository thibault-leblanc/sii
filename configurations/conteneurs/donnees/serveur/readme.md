# 📥 Serveur FTP (Ingestion des données)

Ce conteneur fournit un service FTP léger et sécurisé basé sur `vsftpd` et Alpine Linux. Il est destiné à être exposé sur des réseaux spécifiques (VLAN) via Macvlan pour permettre aux équipements industriels d'y déposer leurs fichiers.

## ⚙️ Fonctionnement

Le conteneur est configuré pour :
* Créer automatiquement un utilisateur au démarrage via des variables d'environnement (`FTP_USER` et `FTP_PASS`).
* Mapper un volume hôte persistant pour stocker les fichiers reçus (`/partage`).
* Configurer les ports passifs (21000-21010) pour s'adapter aux environnements conteneurisés.

## 🚀 Utilisation et Déploiement

### 1. Construction de l'image de base

```bash
docker build -t serveur-ftp:latest .
```
*(L'image peut ensuite être exportée via `docker save` pour un transfert vers l'hôte de production).*

### 2. Déploiement dynamique

Le script `deploiement_ftp.sh` permet de déployer une instance du serveur sur un VLAN spécifique en générant le fichier `docker-compose.yml` associé.

**Syntaxe :**
```bash
./deploiement_ftp.sh <NOM_CONTENEUR> <IP_CONTENEUR> <NOM_MACVLAN> <DOSSIER_PHYSIQUE>
```

**Exemple de déploiement sur le VLAN 20 :**
```bash
./deploiement_ftp.sh donnees-vlan-20 192.168.20.30 vlan20 /home/pi51/donnees/vlan20
```

Le script se chargera de créer les dossiers nécessaires sur l'hôte et de lancer le conteneur en mode détaché.