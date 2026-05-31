# Réseau Terrain / IO
sudo docker network create -d macvlan \
  -o parent=eth0.20 \
  --subnet=192.168.20.0/24 \
  --gateway=192.168.20.1 \
  --ip-range=192.168.20.16/28 \
  vlan20

# Réseau SCADA / Supervision
sudo docker network create -d macvlan \
  -o parent=eth0.30 \
  --subnet=192.168.30.0/24 \
  --gateway=192.168.30.1 \
  --ip-range=192.168.30.16/28 \
  vlan30