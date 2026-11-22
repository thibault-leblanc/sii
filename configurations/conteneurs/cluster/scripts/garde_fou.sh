#!/bin/bash
# Garde-fou contre le doublon : un nœud qui ne porte PAS la VIP ne doit faire tourner aucun service piloté.
# Indépendant de keepalived et de ses scripts : quelle que soit la cause (script en échec, nœud surchargé,
# démarrage manuel), un doublon d'IP sur le terrain ne dure pas plus de ~20 s.
VIP=$(cat /etc/keepalived/vip)
IFACE=$(cat /etc/keepalived/iface)
SERVICES=$(cat /etc/keepalived/services)
CONSTATS=0
while true; do
    sleep 10
    if ip -4 addr show "$IFACE" 2>/dev/null | grep -q " $VIP/"; then CONSTATS=0; continue; fi
    EN_MARCHE=$(docker ps --filter status=running --format '{{.Names}}' 2>/dev/null) || continue
    EN_TROP=$(grep -xF "$SERVICES" <<< "$EN_MARCHE" | tr '\n' ' ')
    if [ -z "${EN_TROP// /}" ]; then CONSTATS=0; continue; fi
    CONSTATS=$((CONSTATS + 1))
    if [ "$CONSTATS" -ge 2 ]; then   # deux constats de suite : pas de réaction pendant une transition normale
        echo "$(date -u +%FT%TZ) garde-fou : sans VIP mais $EN_TROP en marche, arrêt"
        # shellcheck disable=SC2086
        docker stop $EN_TROP > /dev/null
        CONSTATS=0
    fi
done
