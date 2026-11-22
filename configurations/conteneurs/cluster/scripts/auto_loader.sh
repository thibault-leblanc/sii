#!/bin/bash
# Charge dans Docker les images déposées dans ~/images du nœud, et SEULEMENT là :
# jamais les données synchronisées depuis le FTP (audit, constat n°1).
# Une image n'est rechargée que si son .tar est plus récent que la marque gardée dans /etat (persistant,
# ~/.agent-ha sur l'hôte) : recharger 130 Mo à chaque démarrage surchargeait le Pi et faussait la sonde.
mkdir -p /etat
while true; do
    for TAR in /config/images/*.tar; do
        [ -f "$TAR" ] || continue
        MARQUE="/etat/$(basename "$TAR").charge"
        if [ ! -f "$MARQUE" ] || [ "$TAR" -nt "$MARQUE" ]; then
            echo "$(date -u +%FT%TZ) chargement de $TAR"
            docker load -i "$TAR" && touch "$MARQUE"
        fi
    done
    sleep 60
done
