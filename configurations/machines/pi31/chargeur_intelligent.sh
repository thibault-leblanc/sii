#!/bin/bash

# Liste des dossiers contenant tes archives
DOSSIERS=("/home/pi/api/rincage" "/home/pi/sim/rincage")

for DOSSIER in "${DOSSIERS[@]}"; do
    # Vérifie si un fichier .tar existe dans le dossier
    for TARFILE in "$DOSSIER"/*.tar; do
        [ -e "$TARFILE" ] || continue
        
        MARQUEUR="$TARFILE.charge"
        
        # Si le marqueur n'existe pas, OU si le .tar est plus récent (-nt) que le marqueur
        if [ ! -f "$MARQUEUR" ] || [ "$TARFILE" -nt "$MARQUEUR" ]; then
            echo "[$(date)] Nouvelle image détectée : $TARFILE. Chargement en cache..."
            docker load -i "$TARFILE"
            # Met à jour la date du marqueur
            touch "$MARQUEUR"
        fi
    done
done