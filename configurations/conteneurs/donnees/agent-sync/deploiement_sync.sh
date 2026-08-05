#!/bin/bash

if [ "$#" -ne 3 ]; then
    echo "❌ Erreur : 3 paramètres requis."
    echo "Usage: $0 <NUMERO_VLAN> <IP_CONTENEUR> <NOM_MACVLAN>"
    echo "Exemple: $0 20 192.168.20.31 vlan20"
    exit 1
fi

VLAN=$1
IP_CONTENEUR=$2
MACVLAN=$3

NOM_CONTENEUR="sync-vlan-${VLAN}"
DOSSIER_PHYSIQUE="/home/pi51/donnees/vlan${VLAN}/donnees"
DOSSIER_COMPOSE="$(pwd)/${NOM_CONTENEUR}"
IMAGE_TAR="$(pwd)/agent-sync.tar"

echo "🚀 Déploiement de l'agent de synchronisation : $NOM_CONTENEUR..."

# Chargement de l'image
if [ -f "$IMAGE_TAR" ]; then
    echo "📦 Chargement de l'image source..."
    docker load -i "$IMAGE_TAR"
else
    echo "❌ Fichier $IMAGE_TAR introuvable."
    exit 1
fi

# Génération de l'infrastructure YAML
echo "📝 Génération du fichier docker-compose..."
mkdir -p "$DOSSIER_COMPOSE"
cd "$DOSSIER_COMPOSE" || exit

cat <<EOF > docker-compose.yml
services:
  $NOM_CONTENEUR:
    image: agent-sync:latest
    container_name: $NOM_CONTENEUR
    restart: unless-stopped
    environment:
      - VLAN_CIBLE=vlan${VLAN}
    volumes:
      # Montage en lecture seule (ro) des données pour la sécurité
      - $DOSSIER_PHYSIQUE:/donnees:ro
      # Montage en lecture seule de la clé SSH de pi51
      - /home/pi51/.ssh/id_rsa:/root/.ssh/id_rsa:ro
    networks:
      reseau_macvlan:
        ipv4_address: $IP_CONTENEUR

networks:
  reseau_macvlan:
    external: true
    name: $MACVLAN
EOF

# Démarrage
echo "🐳 Démarrage de l'agent..."
docker compose up -d --force-recreate

echo "✅ Agent déployé. La synchronisation est active en tâche de fond."