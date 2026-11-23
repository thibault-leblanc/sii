"""Relit NetBox et réécrit le modèle au format sii.yaml.

    python outils/exporter.py -o donnees/sii.yaml              # NetBox -> fichier (copie versionnée dans git)
    python outils/exporter.py --comparer donnees/sii.yaml      # contrôle d'aller-retour après un import

Variables : NETBOX_URL, NETBOX_TOKEN (comme importer.py).
"""
import argparse
import ipaddress
import sys
from pathlib import Path

from importer import connecter, parent_de
from modele import (INTERFACE_PHYSIQUE, charger, console_utf8, differences, ecrire_yaml, normaliser,
                    ports_compacts)

ENTETE = ("# Export de NetBox par netbox/outils/exporter.py. NetBox fait foi : modifier NetBox,\n"
          "# puis relancer l'export. Les points à vérifier (a_verifier) ne vivent pas dans NetBox.\n")


def valeur(champ):
    """Les champs à choix de l'API sont des objets {value, label}."""
    return champ.get("value") if isinstance(champ, dict) else champ


def tout(ep, **filtres):
    return [dict(o) for o in (ep.filter(**filtres) if filtres else ep.all())]


def exporter(nb, slug_site="sii-lab"):
    site = dict(nb.dcim.sites.get(slug=slug_site))
    m = {"site": {"nom": site["name"], "slug": site["slug"]}}
    ctx = nb.extras.config_contexts.get(name="sii-reseau")
    m["dns"] = dict(ctx)["data"].get("dns", []) if ctx else []

    ips = tout(nb.ipam.ip_addresses)
    ips_de = {}
    for ip in ips:
        ips_de.setdefault((ip["assigned_object_type"], ip["assigned_object_id"]), []).append(ip)

    groupe = nb.ipam.vlan_groups.get(slug="sii")
    prefixes = tout(nb.ipam.prefixes)
    plages = tout(nb.ipam.ip_ranges, tag="macvlan")
    m["vlans"] = {}
    for v in sorted(tout(nb.ipam.vlans, group_id=groupe.id), key=lambda v: v["vid"]):
        entree = {"nom": v["name"], "description": v["description"]}
        pre = next((p for p in prefixes if (p.get("vlan") or {}).get("id") == v["id"]), None)
        if pre:
            entree["prefixe"] = pre["prefix"]
            reseau = ipaddress.ip_network(pre["prefix"])
            for r in plages:
                debut = ipaddress.ip_interface(r["start_address"]).ip
                fin = ipaddress.ip_interface(r["end_address"]).ip
                if debut in reseau:
                    blocs = list(ipaddress.summarize_address_range(debut, fin))
                    entree["plage_macvlan"] = str(blocs[0]) if len(blocs) == 1 else f"{debut}-{fin}"
        m["vlans"][v["vid"]] = entree

    m["roles"] = {r["slug"]: {"nom": r["name"], "couleur": r["color"], **({"vm": True} if r.get("vm_role") else {})}
                  for r in tout(nb.dcim.device_roles)}
    m["plateformes"] = {p["slug"]: p["name"] for p in tout(nb.dcim.platforms)}
    m["types"] = {t["slug"]: {"fabricant": t["manufacturer"]["name"], "modele": t["model"]}
                  for t in tout(nb.dcim.device_types)}
    m["clusters"] = {c["name"]: c["description"] for c in tout(nb.virtualization.clusters, type="sii")}

    appareils = tout(nb.dcim.devices, site_id=site["id"])
    role_de = {d["name"]: d["role"]["slug"] for d in appareils}
    nom_appareil = {d["id"]: d["name"] for d in appareils}
    m["equipements"] = {}
    for d in appareils:
        eq = {"type": d["device_type"]["slug"], "role": d["role"]["slug"]}
        if d.get("platform"):
            eq["plateforme"] = d["platform"]["slug"]
        # Appartenance à plusieurs clusters : champ personnalisé « clusters » (le champ natif n'en porte qu'un).
        clusters = [c["name"] for c in (d.get("custom_fields") or {}).get("clusters") or []]
        if not clusters and d.get("cluster"):
            clusters = [d["cluster"]["name"]]
        if clusters:
            eq["clusters"] = clusters
        if d.get("description"):
            eq["description"] = d["description"]
        if d.get("local_context_data"):
            eq["contexte"] = d["local_context_data"]
        principale = (d.get("primary_ip4") or {}).get("id")
        eq["interfaces"] = {}
        for i in tout(nb.dcim.interfaces, device_id=d["id"]):
            e = {}
            if i.get("parent"):
                e["parent"] = i["parent"]["name"]
            if valeur(i["type"]) != ("virtual" if i.get("parent") else INTERFACE_PHYSIQUE):
                e["type"] = valeur(i["type"])
            mode = valeur(i.get("mode"))
            if mode == "access" and i.get("untagged_vlan"):
                e["vlan"] = i["untagged_vlan"]["vid"]
            elif mode == "tagged":
                e["vlans"] = sorted(v["vid"] for v in i.get("tagged_vlans") or [])
            ip_itf = ips_de.get(("dcim.interface", i["id"]), [])
            if ip_itf:
                e["ip"] = ip_itf[0]["address"]
                if ip_itf[0]["id"] == principale:
                    e["principale"] = True
            if i.get("description"):
                e["description"] = i["description"]
            pairs = i.get("link_peers") or []
            if pairs and role_de[d["name"]] != "commutateur":
                pair = pairs[0]["device"]["name"]
                if role_de.get(pair) == "commutateur" or d["name"] < pair:
                    e["cable"] = f"{pair}/{pairs[0]['name']}"
            eq["interfaces"][i["name"]] = e
        m["equipements"][d["name"]] = eq

    m["vrrp"] = {}
    for g in tout(nb.ipam.fhrp_groups):
        affectations = tout(nb.ipam.fhrp_group_assignments, group_id=g["id"])
        vip = ips_de.get(("ipam.fhrpgroup", g["id"]), [{}])[0].get("address")
        m["vrrp"][g["name"]] = {
            "vrid": g["group_id"], "vip": vip,
            "interface": affectations[0]["interface"]["name"] if affectations else None,
            "membres": {a["interface"]["device"]["name"]: a["priority"] for a in affectations}}

    vms = tout(nb.virtualization.virtual_machines)
    nom_vm = {v["id"]: v["name"] for v in vms}
    m["services"] = {}
    for v in vms:
        s = {"cluster": v["cluster"]["name"]}
        if any(t["slug"] == "ha" for t in v.get("tags") or []):
            s["ha"] = True
        if v.get("description"):
            s["description"] = v["description"]
        ctx = v.get("local_context_data") or {}
        for cle in ("source", "chemin", "passerelle", "fichiers", "amorcage"):
            if cle in ctx:
                s[cle] = ctx[cle]
        ip_vm = {}
        for vi in tout(nb.virtualization.interfaces, virtual_machine_id=v["id"]):
            for ip in ips_de.get(("virtualization.vminterface", vi["id"]), []):
                ip_vm[vi["name"]] = ip["address"]
        if ip_vm:
            s["ip"] = ip_vm
        if "compose" in ctx:
            s["compose"] = ctx["compose"]
        m["services"][v["name"]] = s

    for sv in tout(nb.ipam.services):
        type_parent, id_parent = parent_de(sv)
        if type_parent == "dcim.device":
            cible = m["equipements"].get(nom_appareil.get(id_parent))
        else:
            cible = m["services"].get(nom_vm.get(id_parent))
        if cible is None:
            continue
        p = {"proto": valeur(sv["protocol"]), "ports": ports_compacts(sv["ports"])}
        if sv.get("ipaddresses"):
            p["ip"] = sv["ipaddresses"][0]["address"]
        clients = (sv.get("custom_fields") or {}).get("clients")
        if clients:
            p["clients"] = clients
        if sv.get("description"):
            p["description"] = sv["description"]
        cible.setdefault("ports", {})[sv["name"]] = p
    return m


def main():
    console_utf8()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("-o", "--sortie", help="fichier YAML à écrire (sinon : sortie standard)")
    p.add_argument("--comparer", help="fichier source à comparer à l'export (contrôle d'aller-retour)")
    p.add_argument("--site", default="sii-lab")
    args = p.parse_args()
    m = exporter(connecter(), args.site)
    if args.comparer:
        source = charger(args.comparer)
        ecarts = differences(normaliser(source), normaliser(m))
        for e in ecarts:
            print(f"  ✗ {e}")
        print(f"Aller-retour : {len(ecarts)} écart(s) entre {args.comparer} et NetBox.")
    if args.sortie:
        # La liste a_verifier n'existe pas dans NetBox : on garde celle du fichier remplacé.
        if Path(args.sortie).exists() and charger(args.sortie).get("a_verifier"):
            m = {"a_verifier": charger(args.sortie)["a_verifier"], **m}
        ecrire_yaml(m, args.sortie, ENTETE)
        print(f"Écrit : {args.sortie}")
    elif not args.comparer:
        print(ecrire_yaml(m, entete=ENTETE))
    sys.exit(1 if args.comparer and ecarts else 0)


if __name__ == "__main__":
    main()
