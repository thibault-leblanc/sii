# Préparation des nœuds

Ce qui s'applique **à l'hôte** (Ubuntu Server 26.04, arm64) et ne vient pas de NetBox. Le réseau de l'hôte
(netplan) et les réseaux Docker (macvlan) sont générés depuis NetBox (`netbox/genere/<nœud>/`).

| Fichier | Rôle | Application |
|---|---|---|
| `installation_docker.sh` | Installe Docker Engine et Compose (dépôt officiel), ajoute l'utilisateur au groupe `docker`. | `bash installation_docker.sh`, puis nouvelle session |
| `apt/20auto-upgrades` | **Désactive les mises à jour automatiques** : elles redémarraient Docker, donc le procédé (2026-11-23). | `sudo install -m 644 apt/20auto-upgrades /etc/apt/apt.conf.d/` puis `sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer unattended-upgrades` |

Conventions : compte et nom d'hôte = nom du nœud (`pi31`…), données dans `~/donnees/vlanXX/donnees`, images dans
`~/images`. Procédure complète de (ré)installation : `netbox/README.md`, « (Ré)installer un nœud ».

Mettre à jour un nœud (paquets) : décision explicite, **nœud passif d'abord** ; sur le maître, basculer avant
(`docker stop ha-cluster`), mettre à jour, puis relancer l'agent.
