#!/bin/sh
# Construit les images de la plateforme pour les Pi (arm64) et les enregistre en .tar dans configurations/images/.
# À lancer depuis le poste d'administration (Docker Desktop émule arm64) :
#   sh configurations/construire_images.sh            # toutes les images
#   sh configurations/construire_images.sh agent-ha    # une seule
#
# Déploiement : voir netbox/README.md, « Images corrigées ».
# Vérifier une fois sur un Pi que `uname -m` affiche aarch64 (sinon changer PLATEFORME).
set -e
PLATEFORME=linux/arm64
cd "$(dirname "$0")"
mkdir -p images

construire() {  # <nom du .tar> <tag de l'image> <dossier>
  case " $SELECTION " in *" $1 "*|"  ") ;; *) return ;; esac
  echo "== $2 ($3)"
  docker buildx build --platform "$PLATEFORME" -t "$2" --load "$3"
  docker save -o "images/$1.tar" "$2"
  echo "   -> images/$1.tar"
}

SELECTION="$*"
construire api-rincage   api-rincage-image:latest  conteneurs/api/rincage
construire sim-rincage   simu-rincage-image:latest conteneurs/sim/rincage
construire agent-ha      agent-ha:latest           conteneurs/cluster
construire agent-sync    agent-sync:latest         conteneurs/donnees/agent-sync
construire serveur-ftp   serveur-ftp:latest        conteneurs/donnees/serveur
