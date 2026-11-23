#!/bin/bash
# Sonde VRRP : code 0 = nœud sain ; trois échecs de suite = FAULT (le nœud lâche la VIP).
# - Sur un nœud BACKUP, /tmp/force_backup rend la sonde saine : ses services sont arrêtés exprès,
#   il doit rester candidat (pas en FAULT) pour pouvoir prendre la main.
# - Sur le maître : sain seulement si CHAQUE service piloté tourne (audit H3).
[ -f /tmp/force_backup ] && exit 0
EN_MARCHE=$(docker ps --filter status=running --format '{{.Names}}') || exit 1
while read -r SERVICE; do
    [ -n "$SERVICE" ] || continue
    grep -qx "$SERVICE" <<< "$EN_MARCHE" || exit 1
done < /etc/keepalived/services
exit 0
