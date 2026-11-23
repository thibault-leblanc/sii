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

# Avant de démarrer : chaque IP de service doit être libre sur le terrain (détection d'adresse en double, ARP).
# L'ancien maître peut mettre plusieurs secondes à arrêter ses services ; démarrer avant créerait un doublon d'IP
# (constaté le 2026-11-23 sur le simulateur, audit H6). Attente bornée à 90 s, abandonnée si l'état voulu change.
adresses_libres() {
    local debut=$SECONDS
    while read -r IP ITF; do
        [ -n "$IP" ] || continue
        until arping -D -q -c 2 -w 3 -I "$ITF" "$IP"; do
            [ "$(cat /tmp/etat_voulu)" = "MASTER" ] || return 1
            [ $((SECONDS - debut)) -lt 90 ] || return 1
            journal "IP $IP encore active sur le réseau, attente de son arrêt ailleurs"
            sleep 2
        done
    done < /etc/keepalived/adresses
}

while true; do
    VOULU=$(cat /tmp/etat_voulu)
    # Premier BACKUP au démarrage de l'agent : rien à arrêter (sinon on couperait le procédé du maître, audit n°3),
    # mais on pose force_backup comme pour tout BACKUP, sinon sa sonde échoue (services arrêtés), il passe en FAULT
    # et ne peut plus prendre la main en cas de panne du maître.
    if [ "$VOULU" = "BACKUP" ] && [ -f /tmp/demarrage ]; then
        rm -f /tmp/demarrage
        touch /tmp/force_backup
        journal "BACKUP au démarrage, services laissés en l'état"
    elif [ "$VOULU" = "MASTER" ]; then
        rm -f /tmp/demarrage /tmp/force_backup
        if adresses_libres; then
            journal "MASTER, démarrage de $SERVICES"
            # shellcheck disable=SC2086
            docker start $SERVICES > /dev/null || journal "ERREUR : conteneur absent, lancer « docker compose create » dans son dossier"
        elif [ "$(cat /tmp/etat_voulu)" = "MASTER" ]; then
            journal "ERREUR : IP de service toujours active ailleurs après 90 s, services NON démarrés (pas de doublon)"
        fi
    else
        rm -f /tmp/demarrage
        touch /tmp/force_backup
        journal "$VOULU, arrêt de $SERVICES"
        # shellcheck disable=SC2086
        docker stop $SERVICES > /dev/null
    fi
    [ "$(cat /tmp/etat_voulu)" = "$VOULU" ] && break   # un nouvel état est arrivé pendant l'action : on le rejoue
done
