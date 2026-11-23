# Agent de haute disponibilité : keepalived (VRRP) + pilotage des conteneurs du nœud par le socket Docker.
# Version figée (audit R4) : alpine:latest change sans prévenir.
FROM alpine:3.24.4

# Le paquet keepalived ne crée pas /etc/keepalived : sans lui, l'entrypoint ne pouvait pas écrire
# la configuration et l'agent s'arrêtait aussitôt (constaté le 2026-11-22, déjà vrai sur l'image d'août).
# iputils-arping : vérifier qu'une IP de service est libre avant de démarrer le service (audit H6).
RUN apk add --no-cache keepalived docker-cli python3 bash iputils-arping && \
    mkdir -p /etc/keepalived

# Scripts en fichiers (audit, constat n°8) : lisibles, testables. Les fins de ligne Windows sont retirées,
# un script en CRLF ne s'exécute pas sous Linux.
COPY scripts/*.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/*.sh && chmod 755 /usr/local/bin/*.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
