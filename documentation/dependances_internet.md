# Registre des dépendances à internet

Tenu selon le mode opératoire (`modop_chaine_livraison.md`, §2). Une ligne par dépendance ; le statut est mis à jour
quand elle est remplacée. Relevé initial : lot 0, 2026-11-26 (configuration des trois Pi et du dépôt).

| Dépendance | Nœud | Usage | Voie | Remplacement prévu | Statut |
|---|---|---|---|---|---|
| DNS `1.1.1.1`, `8.8.8.8` (netplan, `eth0.10`) | pi31, pi32, pi51 | Exécution | Direct | Résolveur local (lot D) | En place |
| Heure : `ntp.ubuntu.com` en NTS (chrony, pools 1 à 4 et bootstrap) | pi31, pi32, pi51 | Exécution | Direct | chrony sur pi51 (lot D) | En place |
| Paquets Ubuntu (`archive`, `security.ubuntu.com`) | pi31, pi32, pi51 | Installation | Direct | Passage par le sas, miroir si besoin (lot D) | En place |
| Paquets Docker (`download.docker.com`) | pi31, pi32, pi51 | Installation | Direct | Idem (lot D) | En place |
| Images de base Docker Hub (`python:3.11-slim`, `alpine`, `frangoteam/fuxa`) | Sas | Construction | Sas | Registre local (lots A, B) | En place |
| pip (`requirements.txt` de l'automate et du simulateur) | Sas | Construction | Sas | À décider | En place |
| apk (agent HA, serveur FTP, agent de synchro) | Sas | Construction | Sas | À décider | En place |
| apt dans l'image Python (`gcc`, `libffi-dev`, `libssl-dev`) | Sas | Construction | Sas | À décider | En place |
| npm (`modbus-serial`, `node-opcua`, images SCADA) | Sas | Construction | Sas | À décider | En place |
| Image du registre (`registry:3.1.2`, Docker Hub) | pi51 | Installation | Sas (`docker save`, chargée sur pi51) | Archive `.tar` hors git (lot B) | En place |
| Images NetBox (`netbox-docker`) et pip des outils (`pynetbox`) | Sas | Installation | Sas | Lot E | En place |
| CDN de l'interface `iaac/` (cdnjs `jsoneditor`, unpkg `vis-network`, Google Fonts) | Sas (navigateur) | Exécution | Sas | Copies locales | En place |
| CDN de `netbox/genere/topologie.html` (unpkg `vis-network@9.1.9`) | Sas (navigateur) | Consultation | Sas | Copie locale | En place |
| GitHub (`git push`, liens générés par `vers_iaac.py`) | Sas | Déploiement, documentation | Sas | Dépôt local (lot C), forge (lot E) | En place |

Aucun nœud n'utilise de registre d'images en exécution (`/etc/docker/daemon.json` absent sur les trois Pi) : les
images sont chargées depuis des archives `.tar`.
