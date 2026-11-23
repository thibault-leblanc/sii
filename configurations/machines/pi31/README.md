# Archive : script propre à pi31 (`machines/pi31/`)

**Non utilisé.** `opcua-srv.sh` écrivait et lançait sur le nœud un serveur OPC-UA de test (Dockerfile, compose,
code), variante en script de [`../../conteneurs/opcua-srv/`](../../conteneurs/opcua-srv/README.md).

⚠️ Il utilise les IP 192.168.20.30 et 192.168.30.30, aujourd'hui celles des serveurs FTP (audit D11).

Les fichiers propres à un nœud (netplan, réseaux macvlan, compose) sont désormais générés depuis NetBox
(`netbox/genere/pi31/`). Candidat à la suppression.
