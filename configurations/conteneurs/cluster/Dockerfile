FROM alpine:latest

RUN apk add --no-cache keepalived docker-cli python3 bash

# 1. Le script d'Auto-Chargement des images (Warm Standby)
RUN echo '#!/bin/bash' > /auto_loader.sh && \
    echo 'while true; do' >> /auto_loader.sh && \
    echo '  # Scanne tous les fichiers .tar dans le dossier partagé' >> /auto_loader.sh && \
    echo '  for TARFILE in $(find /config -name "*.tar"); do' >> /auto_loader.sh && \
    echo '    MARQUEUR="/tmp/$(basename $TARFILE).charge"' >> /auto_loader.sh && \
    echo '    # Si le fichier est nouveau ou mis à jour, on le charge' >> /auto_loader.sh && \
    echo '    if [ ! -f "$MARQUEUR" ] || [ "$TARFILE" -nt "$MARQUEUR" ]; then' >> /auto_loader.sh && \
    echo '      echo "📦 Détection nouvelle image : $TARFILE. Chargement..."' >> /auto_loader.sh && \
    echo '      docker load -i "$TARFILE"' >> /auto_loader.sh && \
    echo '      touch "$MARQUEUR"' >> /auto_loader.sh && \
    echo '    fi' >> /auto_loader.sh && \
    echo '  done' >> /auto_loader.sh && \
    echo '  sleep 60' >> /auto_loader.sh && \
    echo 'done' >> /auto_loader.sh

# 2. Le script principal (Keepalived dynamique)
RUN echo '#!/bin/bash' > /entrypoint.sh && \
    echo 'HOST_NAME=$(hostname)' >> /entrypoint.sh && \
    echo 'VIP=$(python3 -c "import json; print(json.load(open(\"/config/config_cluster.json\"))[\"vip_admin\"])")' >> /entrypoint.sh && \
    echo 'VRID=$(python3 -c "import json; print(json.load(open(\"/config/config_cluster.json\"))[\"vrid\"])")' >> /entrypoint.sh && \
    echo 'IFACE=$(python3 -c "import json; print(json.load(open(\"/config/config_cluster.json\"))[\"interface_heartbeat\"])")' >> /entrypoint.sh && \
    echo 'PRIORITY=$(python3 -c "import json, os; print(json.load(open(\"/config/config_cluster.json\"))[\"services_surveilles\"][\"api-rincage\"].get(f\"priorite_{os.environ.get(\"HOSTNAME\")}\", 90))")' >> /entrypoint.sh && \
    echo 'cat <<EOF > /etc/keepalived/keepalived.conf' >> /entrypoint.sh && \
    echo 'vrrp_script check_docker {' >> /entrypoint.sh && \
    echo '    script "/check_health.sh"' >> /entrypoint.sh && \
    echo '    interval 2' >> /entrypoint.sh && \
    echo '    weight -20' >> /entrypoint.sh && \
    echo '}' >> /entrypoint.sh && \
    echo 'vrrp_instance COEUR_SII {' >> /entrypoint.sh && \
    echo '    state BACKUP' >> /entrypoint.sh && \
    echo '    interface $IFACE' >> /entrypoint.sh && \
    echo '    virtual_router_id $VRID' >> /entrypoint.sh && \
    echo '    priority $PRIORITY' >> /entrypoint.sh && \
    echo '    advert_int 1' >> /entrypoint.sh && \
    echo '    virtual_ipaddress { $VIP/24 }' >> /entrypoint.sh && \
    echo '    track_script { check_docker }' >> /entrypoint.sh && \
    echo '    notify_master "/action.sh MASTER"' >> /entrypoint.sh && \
    echo '    notify_backup "/action.sh BACKUP"' >> /entrypoint.sh && \
    echo '    notify_fault "/action.sh FAULT"' >> /entrypoint.sh && \
    echo '}' >> /entrypoint.sh && \
    echo 'EOF' >> /entrypoint.sh && \
    echo '# Lancement du chargeur d images en tâche de fond' >> /entrypoint.sh && \
    echo '/auto_loader.sh &' >> /entrypoint.sh && \
    echo '# Lancement de Keepalived en processus principal' >> /entrypoint.sh && \
    echo 'exec keepalived -n -l -D' >> /entrypoint.sh

# 3. Sondes et Actions dynamiques
RUN echo '#!/bin/bash' > /check_health.sh && \
    echo 'if [ -f /tmp/force_backup ]; then exit 0; fi' >> /check_health.sh && \
    echo 'PATTERN=$(python3 -c "import json; d=json.load(open(\"/config/config_cluster.json\"))[\"services_surveilles\"]; print(\"|\".join(d.keys()))")' >> /check_health.sh && \
    echo 'docker ps --format "{{.Names}}" | grep -Eq "$PATTERN"' >> /check_health.sh

RUN echo '#!/bin/bash' > /action.sh && \
    echo 'ACTION=$1' >> /action.sh && \
    echo 'LISTE_CONTENEURS=$(python3 -c "import json; d=json.load(open(\"/config/config_cluster.json\"))[\"services_surveilles\"]; print(\" \".join(d.keys()))")' >> /action.sh && \
    echo 'if [ "$ACTION" = "MASTER" ]; then' >> /action.sh && \
    echo '  rm -f /tmp/force_backup' >> /action.sh && \
    echo '  docker start $LISTE_CONTENEURS || python3 -c "' >> /action.sh && \
    echo 'import json, os' >> /action.sh && \
    echo 'd=json.load(open(\"/config/config_cluster.json\"))[\"services_surveilles\"]' >> /action.sh && \
    echo 'for s, v in d.items():' >> /action.sh && \
    echo '    os.system(f\"cd /config/{v[\"chemin_compose\"]} && docker compose up -d\")' >> /action.sh && \
    echo '"' >> /action.sh && \
    echo 'else' >> /action.sh && \
    echo '  touch /tmp/force_backup' >> /action.sh && \
    echo '  docker stop $LISTE_CONTENEURS' >> /action.sh && \
    echo 'fi' >> /action.sh

RUN chmod +x /auto_loader.sh /entrypoint.sh /check_health.sh /action.sh
ENTRYPOINT ["/entrypoint.sh"]