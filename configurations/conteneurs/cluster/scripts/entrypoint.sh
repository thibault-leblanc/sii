#!/bin/bash
# Agent HA : génère la configuration keepalived depuis /config/config_cluster.json (généré depuis NetBox),
# puis lance keepalived au premier plan.
set -euo pipefail
CONF=/config/config_cluster.json

lire() { python3 -c "import json, os, sys; c = json.load(open('$CONF')); print($1)"; }
VIP=$(lire 'c["vip_admin"]')
VRID=$(lire 'c["vrid"]')
IFACE=$(lire 'c["interface_heartbeat"]')
# Priorité du nœud : le réseau de l'hôte (network_mode: host) donne son nom ; 90 si le nœud est inconnu.
PRIORITE=$(lire 'next(iter(c["services_surveilles"].values())).get("priorite_" + os.uname().nodename, 90)')
# Conteneurs pilotés par l'agent, lus une seule fois : la sonde reste légère.
lire '"\n".join(s["nom_conteneur"] for s in c["services_surveilles"].values())' > /etc/keepalived/services
# IP de chaque service et sous-interface où la vérifier par ARP avant de démarrer (voir action.sh).
lire '"\n".join(a["ip"] + " " + a["interface"] for s in c["services_surveilles"].values() for a in s.get("adresses", []))' > /etc/keepalived/adresses
echo "$VIP" > /etc/keepalived/vip
echo "$IFACE" > /etc/keepalived/iface

cat > /etc/keepalived/keepalived.conf <<EOF
global_defs {
    script_user root
    enable_script_security
}
vrrp_script check_docker {
    script "/usr/local/bin/check_health.sh"
    interval 10    # un Pi 3B chargé met jusqu'à plusieurs secondes pour interroger Docker
    timeout 8
    fall 3         # trois échecs de suite (~30 s) : pas de bascule sur un échantillon lent
    rise 2
    # Pas de « weight » : une sonde en échec met le nœud en FAULT (il lâche la VIP).
    # Avec un poids, la priorité baissait (100 -> 80) mais nopreempt interdisait au passif (90)
    # de prendre la main : une panne de service n'aurait jamais provoqué de bascule (2026-11-23).
}
vrrp_instance COEUR_SII {
    state BACKUP
    interface $IFACE
    virtual_router_id $VRID
    priority $PRIORITE
    # Pas de reprise automatique (audit H2) : un nœud qui revient ne reprend pas la main tout seul.
    # Évite les allers-retours (deux redémarrages à froid du procédé) et les bascules en boucle.
    nopreempt
    advert_int 1
    virtual_ipaddress {
        $VIP/24
    }
    track_script {
        check_docker
    }
    notify_master "/usr/local/bin/action.sh MASTER"
    notify_backup "/usr/local/bin/action.sh BACKUP"
    notify_fault "/usr/local/bin/action.sh FAULT"
    # Arrêt de l'agent (mise à jour, redémarrage de Docker) : arrêter aussi les services, sinon le passif
    # prend la main et les démarre pendant qu'ils tournent encore ici (doublon d'IP sur le terrain).
    notify_stop "/usr/local/bin/action.sh STOP"
}
EOF

echo "Agent HA : $(uname -n) priorité $PRIORITE, VIP $VIP, VRID $VRID sur $IFACE, services : $(tr '\n' ' ' < /etc/keepalived/services)"
# Le premier BACKUP vient du démarrage de keepalived, pas d'une perte de maîtrise (voir action.sh).
touch /tmp/demarrage
/usr/local/bin/auto_loader.sh &
/usr/local/bin/garde_fou.sh &
exec keepalived -n -l -D -f /etc/keepalived/keepalived.conf
