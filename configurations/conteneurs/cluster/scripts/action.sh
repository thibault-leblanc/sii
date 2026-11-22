#!/bin/bash
# Appelé par keepalived à chaque changement d'état : MASTER, BACKUP, FAULT, et STOP à l'arrêt de l'agent.
# Les conteneurs pilotés sont créés d'avance sur chaque nœud (docker compose create, voir netbox/README.md) :
# l'agent ne fait que les démarrer ou les arrêter.
#
# keepalived lance ces appels EN PARALLÈLE. Sur un nœud chargé, un « docker start » (MASTER) lent pouvait se
# terminer après le « docker stop » (BACKUP) arrivé 5 s plus tard : services allumés sur le passif, doublon d'IP
# (constaté le 2026-11-22). D'où : on note l'état voulu tout de suite, puis un seul appel à la fois applique
# le DERNIER état voulu, jusqu'à ce qu'il ne change plus.
ACTION=$1
echo "$ACTION" > /tmp/etat_voulu
exec 9> /tmp/action.lock
flock 9

SERVICES=$(tr '\n' ' ' < /etc/keepalived/services)
journal() { echo "$(date -u +%FT%TZ) agent HA : $*" >> /proc/1/fd/1; }

while true; do
    VOULU=$(cat /tmp/etat_voulu)
    # Premier BACKUP au démarrage de l'agent : rien à arrêter (sinon on couperait le procédé du maître, audit n°3),
    # mais on pose force_backup comme pour tout BACKUP, sinon le nœud perd 20 de priorité et ne peut plus reprendre.
    if [ "$VOULU" = "BACKUP" ] && [ -f /tmp/demarrage ]; then
        rm -f /tmp/demarrage
        touch /tmp/force_backup
        journal "BACKUP au démarrage, services laissés en l'état"
    elif [ "$VOULU" = "MASTER" ]; then
        rm -f /tmp/demarrage /tmp/force_backup
        journal "MASTER, démarrage de $SERVICES"
        # shellcheck disable=SC2086
        docker start $SERVICES > /dev/null || journal "ERREUR : conteneur absent, lancer « docker compose create » dans son dossier"
    else
        rm -f /tmp/demarrage
        touch /tmp/force_backup
        journal "$VOULU, arrêt de $SERVICES"
        # shellcheck disable=SC2086
        docker stop $SERVICES > /dev/null
    fi
    [ "$(cat /tmp/etat_voulu)" = "$VOULU" ] && break   # un nouvel état est arrivé pendant l'action : on le rejoue
done
