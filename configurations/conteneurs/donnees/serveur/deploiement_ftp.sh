#!/bin/bash

# 1. Contrôle des paramètres
if [ "$#" -ne 4 ]; then
    echo "❌ Erreur : 4 paramètres requis."
    echo "Usage: $0 <NOM_CONTENEUR> <IP> <NOM_MACVLAN> <DOSSIER_A_EXPOSER>"
    echo "Exemple: $0 ftp-vlan20 192.168.20.30 vlan20 /home/pi51/donnees/vlan20"
    exit 1
fi

NOM_CONTENEUR=$1
IP_CONTENEUR=$2
MACVLAN=$3
DOSSIER_PHYSIQUE=$4

IMAGE_TAR="$(pwd)/serveur-ftp.tar"
DOSSIER_COMPOSE="$(pwd)/$NOM_CONTENEUR"

echo "🚀 Déploiement de $NOM_CONTENEUR sur $IP_CONTENEUR..."

# 2. Chargement systématique de l'image
if [ -f "$IMAGE_TAR" ]; then
    echo "📦 Chargement de l'image..."
    docker load -i "$IMAGE_TAR"
else
    echo "❌ Fichier $IMAGE_TAR introuvable ici."
    exit 1
fi

# 3. Création du dossier cible
echo "📁 Création du dossier : $DOSSIER_PHYSIQUE"
sudo mkdir -p "$DOSSIER_PHYSIQUE"
sudo chmod -R 777 "$DOSSIER_PHYSIQUE"

# 4. Génération de l'IaaC
echo "📝 Génération du fichier YAML..."
mkdir -p "$DOSSIER_COMPOSE"
cd "$DOSSIER_COMPOSE" || exit

cat <<EOF > docker-compose.yml
services:
  $NOM_CONTENEUR:
    image: serveur-ftp:latest
    container_name: $NOM_CONTENEUR
    restart: unless-stopped
    environment:
      - FTP_USER=admin
      - FTP_PASS=admin
    volumes:
      - $DOSSIER_PHYSIQUE:/partage
    networks:
      reseau_macvlan:
        ipv4_address: $IP_CONTENEUR

networks:
  reseau_macvlan:
    external: true
    name: $MACVLAN
EOF

# 5. Lancement
echo "🐳 Démarrage..."
docker compose up -d --force-recreate

echo "✅ Terminé ! Accès FTP disponible sur ftp://$IP_CONTENEUR (User: admin / Pass: admin)"
