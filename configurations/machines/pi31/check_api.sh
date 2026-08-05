#!/bin/bash
# Renvoie un code de succès (0) uniquement si le conteneur tourne
docker ps --format '{{.Names}}' | grep -Eq "^api-rincage$"