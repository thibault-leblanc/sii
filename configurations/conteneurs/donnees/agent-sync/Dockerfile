FROM alpine:latest

RUN apk add --no-cache rsync openssh-client

# Variable d'environnement par défaut
ENV VLAN_CIBLE="vlan20"

# Script de boucle infinie dynamique
RUN echo '#!/bin/sh' > /sync.sh && \
    echo 'echo "🚀 Demarrage de agent Rsync pour $VLAN_CIBLE..."' >> /sync.sh && \
    echo 'while true; do' >> /sync.sh && \
    echo '  rsync -avz --delete -e "ssh -i /root/.ssh/id_rsa -o StrictHostKeyChecking=no" /donnees/ pi31@192.168.10.10:/home/pi31/donnees/${VLAN_CIBLE}/donnees/' >> /sync.sh && \
    echo '  rsync -avz --delete -e "ssh -i /root/.ssh/id_rsa -o StrictHostKeyChecking=no" /donnees/ pi32@192.168.10.11:/home/pi32/donnees/${VLAN_CIBLE}/donnees/' >> /sync.sh && \
    echo '  sleep 60' >> /sync.sh && \
    echo 'done' >> /sync.sh && \
    chmod +x /sync.sh

ENTRYPOINT ["/sync.sh"]