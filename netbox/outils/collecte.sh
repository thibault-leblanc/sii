#!/bin/sh
# Relève l'état réel d'un nœud (réseau de l'hôte, conteneurs, réseaux Docker) en JSON.
# Lecture seule : ne modifie rien.
#
# Depuis le poste d'administration, pour chaque nœud :
#   ssh pi31@192.168.10.10 sh -s < outils/collecte.sh > collecte/pi31.json
# Puis : python outils/derive.py collecte/
set -e
command -v docker >/dev/null || { echo "docker absent" >&2; exit 1; }

conteneurs=$(docker ps -aq)
reseaux=$(docker network ls -q --filter driver=macvlan)

printf '{\n"hote": "%s",\n' "$(hostname)"
printf '"adresses": %s,\n' "$(ip -j addr)"
if [ -n "$conteneurs" ]; then
  printf '"inspect": %s,\n' "$(docker inspect $conteneurs)"
else
  printf '"inspect": [],\n'
fi
if [ -n "$reseaux" ]; then
  printf '"reseaux": %s\n}\n' "$(docker network inspect $reseaux)"
else
  printf '"reseaux": []\n}\n'
fi
