"""Charge le modèle sii.yaml dans NetBox. Idempotent : on peut le relancer sans créer de doublons.

    NETBOX_URL=http://localhost:8000 NETBOX_TOKEN=<jeton> python outils/importer.py donnees/sii.yaml

Requiert NetBox >= 4.3 (services rattachés par parent_object) et pynetbox.
"""
import ipaddress
import os
import sys

from modele import (INTERFACE_PHYSIQUE, ROLE_CONTENEUR, SOURCE_DEFAUT, charger, console_utf8, ports_explicites,
                    slugifier, valider, vid_de_reseau)

VERSION_MINI = (4, 3)


def connecter():
    import pynetbox
    url, jeton = os.environ.get("NETBOX_URL"), os.environ.get("NETBOX_TOKEN")
    if not url or not jeton:
        sys.exit("Définir NETBOX_URL et NETBOX_TOKEN.")
    nb = pynetbox.api(url, token=jeton)
    version = tuple(int(x) for x in nb.version.split(".")[:2])
    if version < VERSION_MINI:
        sys.exit(f"NetBox {nb.version} trop ancien : {'.'.join(map(str, VERSION_MINI))} minimum.")
    return nb


def parent_de(service):
    """(type, id) du parent d'un service NetBox (dict)."""
    return service.get("parent_object_type"), service.get("parent_object_id")


class Importeur:
    def __init__(self, nb, m):
        self.nb, self.m = nb, m
        self.crees = self.modifies = 0
        self.vlan, self.itf, self.dev, self.vm, self.ip = {}, {}, {}, {}, {}

    def assurer(self, ep, filtre, donnees):
        """Crée l'objet s'il n'existe pas, sinon aligne les champs fournis."""
        obj = ep.get(**filtre)
        if obj is None:
            obj = ep.create(donnees)
            self.crees += 1
            print(f"  + {ep.name} {filtre}")
        elif obj.update(donnees):
            self.modifies += 1
            print(f"  ~ {ep.name} {filtre}")
        return obj

    def assurer_ip(self, adresse, type_objet, id_objet, role=None):
        donnees = {"address": adresse, "status": "active",
                   "assigned_object_type": type_objet, "assigned_object_id": id_objet}
        if role:
            donnees["role"] = role
        ip = self.assurer(self.nb.ipam.ip_addresses, {"address": adresse}, donnees)
        self.ip[adresse] = ip.id
        return ip

    def executer(self):
        nb, m = self.nb, self.m

        print("Socle : étiquettes, champ 'clients', site, DNS")
        self.tag = {s: self.assurer(nb.extras.tags, {"slug": s}, {"name": s, "slug": s}).id for s in ("ha", "macvlan")}
        self.assurer(nb.extras.custom_fields, {"name": "clients"}, {
            "name": "clients", "label": "Clients autorisés", "type": "json", "object_types": ["ipam.service"],
            "description": "Équipements ou services autorisés à joindre ce service (matrice de flux)"})
        site = self.assurer(nb.dcim.sites, {"slug": m["site"]["slug"]},
                            {"name": m["site"]["nom"], "slug": m["site"]["slug"], "status": "active"})
        self.assurer(nb.extras.config_contexts, {"name": "sii-reseau"},
                     {"name": "sii-reseau", "weight": 1000, "sites": [site.id], "data": {"dns": m["dns"]}})

        print("VLAN, préfixes, plages macvlan")
        groupe = self.assurer(nb.ipam.vlan_groups, {"slug": "sii"}, {"name": "SII", "slug": "sii"})
        for vid, v in m["vlans"].items():
            vl = self.assurer(nb.ipam.vlans, {"group_id": groupe.id, "vid": vid},
                              {"group": groupe.id, "vid": vid, "name": v["nom"],
                               "description": v.get("description", ""), "status": "active"})
            self.vlan[vid] = vl.id
            self.assurer(nb.ipam.prefixes, {"prefix": v["prefixe"]},
                         {"prefix": v["prefixe"], "vlan": vl.id, "status": "active", "description": v["nom"]})
            if v.get("plage_macvlan"):
                plage = ipaddress.ip_network(v["plage_macvlan"])
                masque = ipaddress.ip_network(v["prefixe"]).prefixlen
                debut = f"{plage.network_address}/{masque}"
                self.assurer(nb.ipam.ip_ranges, {"start_address": debut},
                             {"start_address": debut, "end_address": f"{plage.broadcast_address}/{masque}",
                              "status": "active", "description": f"IPAM macvlan {v['nom']}",
                              "tags": [self.tag["macvlan"]]})

        print("Catalogue : types, rôles, plateformes, clusters")
        types = {}
        for slug, t in m["types"].items():
            fab = self.assurer(nb.dcim.manufacturers, {"slug": slugifier(t["fabricant"])},
                               {"name": t["fabricant"], "slug": slugifier(t["fabricant"])})
            types[slug] = self.assurer(nb.dcim.device_types, {"slug": slug},
                                       {"manufacturer": fab.id, "model": t["modele"], "slug": slug}).id
        roles = {slug: self.assurer(nb.dcim.device_roles, {"slug": slug},
                                    {"name": r["nom"], "slug": slug, "color": r.get("couleur", "9e9e9e"),
                                     "vm_role": bool(r.get("vm"))}).id
                 for slug, r in m["roles"].items()}
        plateformes = {slug: self.assurer(nb.dcim.platforms, {"slug": slug}, {"name": nom, "slug": slug}).id
                       for slug, nom in (m.get("plateformes") or {}).items()}
        ctype = self.assurer(nb.virtualization.cluster_types, {"slug": "sii"}, {"name": "SII", "slug": "sii"})
        clusters = {nom: self.assurer(nb.virtualization.clusters, {"name": nom},
                                      {"name": nom, "type": ctype.id, "status": "active",
                                       "description": desc or ""}).id
                    for nom, desc in m["clusters"].items()}

        print("Équipements, interfaces, IP")
        for nom, eq in m["equipements"].items():
            dev = self.assurer(nb.dcim.devices, {"name": nom, "site_id": site.id}, {
                "name": nom, "device_type": types[eq["type"]], "role": roles[eq["role"]], "site": site.id,
                "status": "active", "platform": plateformes.get(eq.get("plateforme")),
                "cluster": clusters.get(eq.get("cluster")), "description": eq.get("description", ""),
                "local_context_data": eq.get("contexte")})
            self.dev[nom] = dev
            itfs = eq.get("interfaces") or {}
            principale = None
            # Les interfaces parentes d'abord : une sous-interface référence son parent.
            for inom in sorted(itfs, key=lambda n: bool(itfs[n].get("parent"))):
                itf = itfs[inom]
                donnees = {"device": dev.id, "name": inom, "description": itf.get("description", ""),
                           "type": itf.get("type") or ("virtual" if itf.get("parent") else INTERFACE_PHYSIQUE)}
                if itf.get("parent"):
                    donnees["parent"] = self.itf[(nom, itf["parent"])].id
                if "vlan" in itf:
                    donnees |= {"mode": "access", "untagged_vlan": self.vlan[itf["vlan"]], "tagged_vlans": []}
                elif "vlans" in itf:
                    donnees |= {"mode": "tagged", "untagged_vlan": None,
                                "tagged_vlans": [self.vlan[v] for v in itf["vlans"]]}
                self.itf[(nom, inom)] = self.assurer(nb.dcim.interfaces, {"device_id": dev.id, "name": inom}, donnees)
                if itf.get("ip"):
                    ip = self.assurer_ip(itf["ip"], "dcim.interface", self.itf[(nom, inom)].id)
                    if itf.get("principale"):
                        principale = ip.id
            if principale:
                dev.update({"primary_ip4": principale})

        print("Câbles")
        for nom, eq in m["equipements"].items():
            for inom, itf in (eq.get("interfaces") or {}).items():
                if itf.get("cable"):
                    self.cabler(self.itf[(nom, inom)], self.itf[tuple(itf["cable"].split("/"))])

        print("Groupes VRRP")
        for gnom, g in (m.get("vrrp") or {}).items():
            grp = self.assurer(nb.ipam.fhrp_groups, {"name": gnom},
                               {"name": gnom, "protocol": "vrrp2", "group_id": g["vrid"]})
            self.assurer_ip(g["vip"], "ipam.fhrpgroup", grp.id, role="vrrp")
            for dnom, priorite in g["membres"].items():
                itf = self.itf[(dnom, g["interface"])]
                cle = {"group_id": grp.id, "interface_type": "dcim.interface", "interface_id": itf.id}
                self.assurer(nb.ipam.fhrp_group_assignments, cle,
                             {"group": grp.id, "interface_type": "dcim.interface", "interface_id": itf.id,
                              "priority": priorite})

        print("Services (machines virtuelles)")
        for snom, s in (m.get("services") or {}).items():
            vm = self.assurer(nb.virtualization.virtual_machines, {"name": snom, "cluster_id": clusters[s["cluster"]]}, {
                "name": snom, "cluster": clusters[s["cluster"]], "role": roles[ROLE_CONTENEUR], "status": "active",
                "description": s.get("description", ""), "tags": [self.tag["ha"]] if s.get("ha") else [],
                "local_context_data": {k: s[k] for k in ("source", "chemin", "compose") if k in s}})
            self.vm[snom] = vm
            for reseau, adresse in (s.get("ip") or {}).items():
                vi = self.assurer(nb.virtualization.interfaces, {"virtual_machine_id": vm.id, "name": reseau},
                                  {"virtual_machine": vm.id, "name": reseau, "mode": "access",
                                   "untagged_vlan": self.vlan[vid_de_reseau(reseau)]})
                self.assurer_ip(adresse, "virtualization.vminterface", vi.id)

        print("Ports exposés et clients autorisés")
        for nom, eq in m["equipements"].items():
            self.ports(eq.get("ports"), ("dcim.device", self.dev[nom].id))
        for snom, s in (m.get("services") or {}).items():
            self.ports(s.get("ports"), ("virtualization.virtualmachine", self.vm[snom].id))

        print(f"Terminé : {self.crees} création(s), {self.modifies} modification(s).")

    def cabler(self, a, b):
        a = dict(self.nb.dcim.interfaces.get(a.id))
        pairs = [p["id"] for p in a.get("link_peers") or []]
        if pairs == [b.id]:
            return
        if pairs:
            print(f"  ! {a['device']['name']}/{a['name']} est déjà câblée ailleurs : câble non modifié")
            return
        self.nb.dcim.cables.create({
            "a_terminations": [{"object_type": "dcim.interface", "object_id": a["id"]}],
            "b_terminations": [{"object_type": "dcim.interface", "object_id": b.id}],
            "status": "connected"})
        self.crees += 1
        print(f"  + câble {a['device']['name']}/{a['name']} <-> {b.device.name}/{b.name}")

    def ports(self, ports, parent):
        for pnom, p in (ports or {}).items():
            donnees = {"name": pnom, "protocol": p["proto"], "ports": ports_explicites(p["ports"]),
                       "parent_object_type": parent[0], "parent_object_id": parent[1],
                       "description": p.get("description", ""),
                       "ipaddresses": [self.ip[p["ip"]]] if p.get("ip") else [],
                       "custom_fields": {"clients": sorted(p.get("clients") or [])}}
            existant = next((s for s in self.nb.ipam.services.filter(name=pnom) if parent_de(dict(s)) == parent), None)
            if existant is None:
                self.nb.ipam.services.create(donnees)
                self.crees += 1
                print(f"  + service {pnom} sur {parent}")
            elif existant.update(donnees):
                self.modifies += 1
                print(f"  ~ service {pnom} sur {parent}")


def main():
    console_utf8()
    m = charger(sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT)
    erreurs, _ = valider(m)
    if erreurs:
        sys.exit("Modèle invalide, lancer outils/modele.py pour le détail.")
    Importeur(connecter(), m).executer()


if __name__ == "__main__":
    main()
