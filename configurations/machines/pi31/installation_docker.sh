#!/bin/bash
set -e # Arrête le script immédiatement en cas d'erreur

# 1. Prérequis
sudo apt-get update
sudo apt-get install -y ca-certificates curl

# 2. Ajout de la clé GPG
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# 3. Ajout du dépôt
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Installation de Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Configuration de l'utilisateur courant
# (Le groupe docker est généralement déjà créé par l'installation précédente, le || true évite une erreur si c'est le cas)
sudo groupadd docker || true
sudo usermod -aG docker $USER

echo "============================================================"
echo "Installation terminée avec succès !"
echo "⚠️  Action requise : Tapez la commande suivante dans votre terminal"
echo "pour appliquer les droits (ou déconnectez/reconnectez-vous) :"
echo "newgrp docker"
echo "============================================================"