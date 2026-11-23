"""Migration NetBox du 2026-11-23 : cluster « conduite » et SCADA sur pi51. Relançable sans effet de bord.

    NETBOX_URL=... NETBOX_TOKEN=... python netbox/migrations/2026-11-23_conduite_scada.py

Contenu (voir documentation/journal_exploitation.md, 2026-11-23) :
- champ personnalisé « clusters » (plusieurs clusters par nœud) ; rempli depuis le champ natif ;
- cluster « conduite » (fonction de conduite : SCADA) ; pi51 dans infra ET conduite (pi52 à venir) ;
- poste d'administration : 192.168.1.26, côté WAN du pare-feu (et non 192.168.10.49 sur le VLAN10) ;
- service « scada » (FUXA 1.3.3) en 192.168.30.10, IHM tcp/1881 pour le poste d'administration ;
- automate : client OPC-UA « scada » autorisé, route par défaut par le VLAN30 (routage asymétrique corrigé),
  configurations versionnées attachées (config_api.json, config_simu.json).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outils"))
from importer import Importeur, connecter, parent_de  # noqa: E402
from modele import console_utf8  # noqa: E402

CONTENEURS = "configurations/conteneurs"


def main():
    console_utf8()
    nb = connecter()
    imp = Importeur(nb, {})

    print("Champ « clusters » et cluster « conduite »")
    imp.assurer(nb.extras.custom_fields, {"name": "clusters"}, {
        "name": "clusters", "label": "Clusters", "type": "multiobject", "object_types": ["dcim.device"],
        "related_object_type": "virtualization.cluster",
        "description": "Tous les clusters du nœud (le champ natif n'en porte qu'un, le principal)"})
    ctype = nb.virtualization.cluster_types.get(slug="sii")
    conduite = imp.assurer(nb.virtualization.clusters, {"name": "conduite"}, {
        "name": "conduite", "type": ctype.id, "status": "active",
        "description": "Fonction de conduite : SCADA. pi51 aujourd'hui, pi52 demain."})

    print("Appartenance des nœuds")
    for d in nb.dcim.devices.all():
        voulus = [d.cluster.id] if d.cluster else []
        if d.name == "pi51":
            voulus.append(conduite.id)
        if voulus and sorted(c["id"] for c in (dict(d)["custom_fields"].get("clusters") or [])) != sorted(voulus):
            d.update({"custom_fields": {"clusters": voulus}})
            print(f"  ~ {d.name} : {len(voulus)} cluster(s)")

    print("Poste d'administration : côté WAN")
    poste = nb.dcim.devices.get(name="poste-admin")
    poste.update({"description": "Poste d'administration, côté WAN du pare-feu (réseau de la box) : NetBox, "
                                 "construction des images, FUXA de développement (scada-dev)"})
    eth0 = nb.dcim.interfaces.get(device_id=poste.id, name="eth0")
    eth0.update({"mode": None, "untagged_vlan": None, "tagged_vlans": [],
                 "description": "Réseau de la box (192.168.1.0/24), routes vers les VLAN par 192.168.1.200"})
    ip = nb.ipam.ip_addresses.get(assigned_object_type="dcim.interface", assigned_object_id=eth0.id)
    if ip and ip.address != "192.168.1.26/24":
        ip.update({"address": "192.168.1.26/24"})
        print("  ~ IP 192.168.10.49 -> 192.168.1.26")
    for sv in nb.ipam.services.filter(name="fuxa"):
        if parent_de(dict(sv)) == ("dcim.device", poste.id):
            sv.update({"description": "FUXA de développement (conteneur scada-dev du poste), hors plateforme"})

    print("Service scada")
    role = nb.dcim.device_roles.get(slug="conteneur")
    vlan30 = nb.ipam.vlans.get(vid=30, group_id=nb.ipam.vlan_groups.get(slug="sii").id)
    scada = imp.assurer(nb.virtualization.virtual_machines, {"name": "scada", "cluster_id": conduite.id}, {
        "name": "scada", "cluster": conduite.id, "role": role.id, "status": "active",
        "description": "SCADA FUXA (IHM de conduite), client OPC-UA de l'automate",
        "local_context_data": {
            "source": f"{CONTENEURS}/scada",
            "chemin": "scada",
            "compose": {"service": "scada", "image": "scada-fuxa:1.3.3", "container_name": "scada",
                        "restart": "unless-stopped", "volumes": ["./appdata:/usr/src/app/FUXA/server/_appdata"]},
            # Amorçage seulement : le projet évolue ensuite dans FUXA, l'état d'exécution n'est jamais écrasé.
            "amorcage": {f"appdata/{f}": f"{CONTENEURS}/scada/donnees/{f}"
                         for f in ("project.fuxap.db", "settings.js", "mysettings.json")}}})
    vi = imp.assurer(nb.virtualization.interfaces, {"virtual_machine_id": scada.id, "name": "vlan30"},
                     {"virtual_machine": scada.id, "name": "vlan30", "mode": "access", "untagged_vlan": vlan30.id})
    imp.assurer_ip("192.168.30.10/24", "virtualization.vminterface", vi.id)
    imp.ports({"ihm": {"proto": "tcp", "ports": [1881], "clients": ["poste-admin"],
                       "description": "Interface web FUXA"}},
              ("virtualization.virtualmachine", scada.id))

    print("Automate et simulateur : passerelle, client scada, configurations")
    api = nb.virtualization.virtual_machines.get(name="api-rincage")
    ctx = dict(api.local_context_data)
    ctx["passerelle"] = "vlan30"
    ctx["fichiers"] = {"config_api.json": f"{CONTENEURS}/api/rincage/config_api.json"}
    api.update({"local_context_data": ctx})
    for sv in nb.ipam.services.filter(name="opcua"):
        if parent_de(dict(sv)) == ("virtualization.virtualmachine", api.id):
            avant = dict(sv)["custom_fields"].get("clients") or []
            clients = sorted(set(avant + ["scada"]))
            if sorted(avant) != clients:
                sv.update({"custom_fields": {"clients": clients}})
                print(f"  ~ opcua : clients {clients}")
    sim = nb.virtualization.virtual_machines.get(name="sim-rincage")
    ctx = dict(sim.local_context_data)
    ctx["fichiers"] = {"config_simu.json": f"{CONTENEURS}/sim/rincage/config_simu.json"}
    sim.update({"local_context_data": ctx})

    print(f"Terminé : {imp.crees} création(s), {imp.modifies} modification(s) suivies.")


if __name__ == "__main__":
    main()
