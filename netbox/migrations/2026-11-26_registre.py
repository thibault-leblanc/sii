"""Migration NetBox du 2026-11-26 : registre d'images local sur pi51 (lot A). Relançable sans effet de bord.

    NETBOX_URL=... NETBOX_TOKEN=... python netbox/migrations/2026-11-26_registre.py

Contenu (voir documentation/modop_chaine_livraison.md, lot A, et configurations/conteneurs/registre/README.md) :
- service « registre » dans le cluster infra : image registry:3.1.2, publié sur l'hôte en 192.168.10.12:5000
  (pas d'IP macvlan), données dans ./data ;
- port tcp/5000 pour le poste d'administration (envoi des images), pi31 et pi32 (tirage).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outils"))
from importer import Importeur, connecter  # noqa: E402
from modele import console_utf8  # noqa: E402


def main():
    console_utf8()
    nb = connecter()
    imp = Importeur(nb, {})
    infra = nb.virtualization.clusters.get(name="infra")
    role = nb.dcim.device_roles.get(slug="conteneur")

    print("Service registre")
    registre = imp.assurer(nb.virtualization.virtual_machines, {"name": "registre", "cluster_id": infra.id}, {
        "name": "registre", "cluster": infra.id, "role": role.id, "status": "active",
        "description": "Registre d'images local (HTTP, sans authentification jusqu'à la GIA)",
        "local_context_data": {
            "source": "configurations/conteneurs/registre",
            "chemin": "registre",
            "compose": {"service": "registre", "image": "registry:3.1.2", "container_name": "registre",
                        "restart": "unless-stopped", "ports": ["192.168.10.12:5000:5000"],
                        "volumes": ["./data:/var/lib/registry"]}}})
    imp.ports({"http": {"proto": "tcp", "ports": [5000], "clients": ["poste-admin", "pi31", "pi32"],
                        "description": "API du registre (envoi depuis le poste, tirage par les nœuds)"}},
              ("virtualization.virtualmachine", registre.id))

    print(f"Terminé : {imp.crees} création(s), {imp.modifies} modification(s) suivies.")


if __name__ == "__main__":
    main()
