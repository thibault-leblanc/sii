#!/bin/sh
# Généré par netbox/outils/generer.py depuis NetBox. Ne pas modifier à la main.
# Réseaux Docker macvlan de pi51. Relançable sans risque.
set -e

docker network inspect vlan20 >/dev/null 2>&1 || docker network create -d macvlan \
  -o parent=eth0.20 --subnet=192.168.20.0/24 --gateway=192.168.20.1 \
  --ip-range=192.168.20.16/28 vlan20
docker network inspect vlan30 >/dev/null 2>&1 || docker network create -d macvlan \
  -o parent=eth0.30 --subnet=192.168.30.0/24 --gateway=192.168.30.1 \
  --ip-range=192.168.30.16/28 vlan30
