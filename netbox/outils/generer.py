"""Génère les fichiers de déploiement depuis le modèle (export de NetBox).

    python outils/generer.py donnees/sii.yaml -o genere/

Écrit, pour chaque nœud, dans genere/<noeud>/ (arborescence du dossier personnel du nœud) :
  99-<noeud>-netplan.yaml        réseau de l'hôte (à installer dans /etc/netplan)
  creation_vlan.sh               réseaux Docker macvlan (idempotent)
  <chemin>/docker-compose.yml    un par service du cluster du nœud
  config_cluster.json            config de l'agent HA (membres d'un groupe VRRP)
et à la racine :
  matrice_flux.md                qui parle à qui, et quels flux traversent le pare-feu
  topologie.html                 vue graphique (à ouvrir dans un navigateur)
  publier.sh                     copie des fichiers sur les nœuds (simulation par défaut)
"""
import argparse
import ipaddress
import json
import shutil
import sys
from pathlib import Path

from modele import (charger, console_utf8, ecrire_yaml, ip_principale, ips_de, membres, passerelle,
                    ports_compacts, ports_explicites, reseaux_macvlan, est_ubuntu, valider)

ENTETE = "# Généré par netbox/outils/generer.py depuis NetBox. Ne pas modifier à la main.\n"


def netplan(m, noeud):
    eq = m["equipements"][noeud]
    ethernets, vlans = {}, {}
    for inom, itf in (eq.get("interfaces") or {}).items():
        conf = {"id": itf["vlan"], "link": itf["parent"]} if itf.get("parent") else {"dhcp4": False, "dhcp6": False}
        if itf.get("ip"):
            ip = ipaddress.ip_interface(itf["ip"])
            conf["dhcp4"] = False
            conf["addresses"] = [str(ip)]
            if itf.get("principale"):
                gw = passerelle(m, ip.network)
                if gw:
                    conf["routes"] = [{"to": "default", "via": gw}]
                conf["nameservers"] = {"addresses": list(m["dns"])}
        (vlans if itf.get("parent") else ethernets)[inom] = conf
    reseau = {"version": 2, "renderer": "networkd", "ethernets": ethernets}
    if vlans:
        reseau["vlans"] = vlans
    return ecrire_yaml({"network": reseau}, entete=ENTETE)


def creation_vlan(m, noeud):
    lignes = ["#!/bin/sh", ENTETE.strip(), f"# Réseaux Docker macvlan de {noeud}. Relançable sans risque.", "set -e", ""]
    for nom, r in reseaux_macvlan(m, noeud).items():
        lignes.append(f"docker network inspect {nom} >/dev/null 2>&1 || docker network create -d macvlan \\\n"
                      f"  -o parent={r['parent']} --subnet={r['subnet']} --gateway={r['gateway']} \\\n"
                      f"  --ip-range={r['ip_range']} {nom}")
    return "\n".join(lignes) + "\n"


ORDRE_COMPOSE = ["image", "container_name", "restart", "network_mode", "privileged", "environment", "volumes"]


def compose(m, snom):
    s = m["services"][snom]
    corps = dict(s["compose"])
    cle = corps.pop("service")
    # Ordre fixe : NetBox renvoie les clés JSON triées à sa façon, la sortie doit rester stable.
    corps = {k: corps[k] for k in sorted(corps, key=lambda k: (ORDRE_COMPOSE + [k]).index(k))}
    ips = s.get("ip") or {}
    if ips:
        corps["networks"] = {r: {"ipv4_address": str(ipaddress.ip_interface(a).ip)} for r, a in ips.items()}
    # Nom de projet explicite : sinon Compose prend le nom du dossier, et api/rincage et simulation/rincage
    # partagent le projet « rincage » (chacun voit l'autre comme orphelin, --remove-orphans le supprimerait).
    doc = {"name": snom, "services": {cle: corps}}
    if ips:
        doc["networks"] = {r: {"external": True} for r in ips}
    return ecrire_yaml(doc, entete=ENTETE)


def config_cluster(m, gnom):
    """Format attendu par l'agent HA actuel (configurations/conteneurs/cluster/Dockerfile)."""
    g = m["vrrp"][gnom]
    cluster = m["equipements"][next(iter(g["membres"]))]["cluster"]
    surveilles = {
        n: {"nom_conteneur": s["compose"]["container_name"], "chemin_compose": s["chemin"],
            **{f"priorite_{d}": p for d, p in g["membres"].items()}}
        for n, s in sorted(m["services"].items()) if s.get("ha") and s["cluster"] == cluster
    }
    conf = {"vip_admin": str(ipaddress.ip_interface(g["vip"]).ip), "vrid": g["vrid"],
            "interface_heartbeat": g["interface"], "services_surveilles": surveilles}
    return json.dumps(conf, indent=2, ensure_ascii=False) + "\n"


def flux(m):
    """Une ligne par (client, service) : IP source, destination et besoin d'une règle de pare-feu."""
    proprietaires = {**{n: e.get("ports") for n, e in m["equipements"].items()},
                     **{n: s.get("ports") for n, s in m.get("services", {}).items()}}
    lignes = []
    for proprio, ports in proprietaires.items():
        for pnom, p in (ports or {}).items():
            cibles = [ipaddress.ip_interface(p["ip"])] if p.get("ip") else ips_de(m, proprio)
            for client in p.get("clients") or [None]:
                ligne = {"service": f"{proprio}/{pnom}", "proto": p["proto"],
                         "ports": ", ".join(map(str, ports_compacts(ports_explicites(p["ports"])))),
                         "client": client, "source": None, "destination": None, "pare_feu": None}
                if client and cibles:
                    commun = [(c, d) for c in ips_de(m, client) for d in cibles if c.network == d.network]
                    src, dst = commun[0] if commun else (ip_principale(m, client), cibles[0])
                    ligne.update(source=str(src.ip) if src else "?", destination=str(dst.ip),
                                 pare_feu="non" if commun else "oui")
                lignes.append(ligne)
    return lignes


def matrice_flux(m):
    texte = [ENTETE.replace("# ", "<!-- ", 1).rstrip() + " -->", "", "# Matrice de flux",
             "", "Un flux marqué « oui » traverse le pare-feu : il faut une règle qui l'autorise.", "",
             "| Client | IP source | Service | Destination | Proto / ports | Pare-feu |",
             "|---|---|---|---|---|---|"]
    for f in sorted(flux(m), key=lambda f: (f["service"], f["client"] or "")):
        if f["client"]:
            texte.append(f"| {f['client']} | {f['source']} | {f['service']} | {f['destination']} "
                         f"| {f['proto']} {f['ports']} | {f['pare_feu']} |")
        else:
            texte.append(f"| *aucun client déclaré* | | {f['service']} | | {f['proto']} {f['ports']} | |")
    return "\n".join(texte) + "\n"


PAGE_TOPOLOGIE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Topologie SII</title>
<!-- Généré par netbox/outils/generer.py depuis NetBox. Ne pas modifier à la main. -->
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  body { margin: 0; font-family: system-ui, sans-serif; background: #fff; }
  #barre { padding: 8px 12px; background: #f1f5f9; border-bottom: 1px solid #cbd5e1; font-size: 14px; }
  #barre label { margin-left: 14px; }
  #graphe { position: absolute; top: 40px; bottom: 0; left: 0; right: 0; }
</style></head>
<body>
<div id="barre"><b>Topologie SII</b>
  <label><input type="checkbox" data-couche="cable" checked> Câbles</label>
  <label><input type="checkbox" data-couche="ip" checked> IP et VLAN</label>
  <label><input type="checkbox" data-couche="cluster" checked> Clusters et VRRP</label>
  <label><input type="checkbox" data-couche="flux"> Flux autorisés (rouge : traverse le pare-feu)</label>
</div>
<div id="graphe"></div>
<script>
const D = __DONNEES__;
const cases = [...document.querySelectorAll('[data-couche]')];
const actives = () => new Set(cases.filter(c => c.checked).map(c => c.dataset.couche));
let visibles = actives();
const liens = new vis.DataView(new vis.DataSet(D.liens), { filter: l => visibles.has(l.couche) });
new vis.Network(document.getElementById('graphe'), { nodes: new vis.DataSet(D.noeuds), edges: liens }, {
  physics: { barnesHut: { gravitationalConstant: -6000, springLength: 170 } },
  interaction: { hover: true },
  edges: { font: { size: 10, align: 'middle' }, smooth: { type: 'continuous' } }
});
cases.forEach(c => c.onchange = () => { visibles = actives(); liens.refresh(); });
</script></body></html>
"""


def topologie(m):
    """Page HTML autonome (vis-network) : équipements, câbles, VLAN, clusters, VRRP et flux."""
    noeuds, liens = [], []

    def lien(couche, de, vers, **options):
        liens.append({"from": de, "to": vers, "couche": couche, **options})

    for vid, v in m["vlans"].items():
        noeuds.append({"id": f"vlan{vid}", "label": f"{v['nom']}\n{v['prefixe']}", "shape": "ellipse",
                       "color": "#e0f2fe", "title": v.get("description", "")})
    for c, desc in m["clusters"].items():
        noeuds.append({"id": f"cluster:{c}", "label": f"cluster {c}", "shape": "database",
                       "color": "#ede9fe", "title": desc or ""})
    for nom, eq in m["equipements"].items():
        ip = ip_principale(m, nom)
        noeuds.append({"id": nom, "label": f"{nom}\n{ip.ip if ip else ''}".strip(), "shape": "box", "borderWidth": 2,
                       "color": {"background": "#ffffff", "border": "#" + m["roles"][eq["role"]].get("couleur", "9e9e9e")},
                       "title": eq.get("description", "")})
        if eq.get("cluster"):
            lien("cluster", nom, f"cluster:{eq['cluster']}", dashes=True, color="#a78bfa")
        for inom, itf in (eq.get("interfaces") or {}).items():
            if itf.get("cable"):
                pair, _, pitf = itf["cable"].partition("/")
                lien("cable", nom, pair, label=f"{inom} ↔ {pitf}", width=2, color="#334155")
            if itf.get("ip") and itf.get("vlan"):
                lien("ip", nom, f"vlan{itf['vlan']}", label=f"{inom} {itf['ip'].split('/')[0]}", color="#0ea5e9")
    for snom, s in (m.get("services") or {}).items():
        noeuds.append({"id": snom, "label": snom, "shape": "hexagon", "size": 14, "color": "#fdba74",
                       "title": s.get("description", "")})
        lien("cluster", snom, f"cluster:{s['cluster']}", dashes=True, color="#a78bfa", label="HA" if s.get("ha") else "")
        for reseau, adresse in (s.get("ip") or {}).items():
            lien("ip", snom, reseau, label=adresse.split("/")[0], color="#10b981")
    for gnom, g in (m.get("vrrp") or {}).items():
        noeuds.append({"id": f"vrrp:{gnom}", "label": f"VIP {g['vip'].split('/')[0]}\nVRID {g['vrid']}",
                       "shape": "diamond", "size": 12, "color": "#c4b5fd"})
        for d, prio in g["membres"].items():
            lien("cluster", f"vrrp:{gnom}", d, label=f"priorité {prio}", dashes=True, color="#a78bfa")
    for f in flux(m):
        if f["client"]:
            traverse = f["pare_feu"] == "oui"
            lien("flux", f["client"], f["service"].split("/")[0], arrows="to", label=f"{f['proto']} {f['ports']}",
                 color="#dc2626" if traverse else "#f59e0b", dashes=traverse)
    donnees = json.dumps({"noeuds": noeuds, "liens": liens}, ensure_ascii=False).replace("</", "<\\/")
    return PAGE_TOPOLOGIE.replace("__DONNEES__", donnees)


def publier(m, noeuds):
    lignes = ["#!/bin/sh", ENTETE.strip(),
              "# Copie genere/<noeud>/ dans le dossier personnel de chaque nœud, par SSH (compte = nom du nœud).",
              "# Sans option : affiche seulement ce qui serait copié.  Pour copier : sh publier.sh --appliquer",
              "# Les fichiers remplacés sont gardés à côté avec le suffixe ~1~, ~2~... (GNU tar --backup).",
              "set -e", 'cd "$(dirname "$0")"', ""]
    for n in noeuds:
        ip = ip_principale(m, n).ip
        lignes += [f'echo "== {n} ({ip})"',
                   'if [ "$1" = "--appliquer" ]; then',
                   # --no-overwrite-dir : ne pas changer les droits de ~ (sshd refuserait les clés)
                   f"  tar -C {n} -cf - . | ssh {n}@{ip} 'tar -C ~ --no-overwrite-dir --backup=numbered -xvf -'",
                   "else",
                   f"  tar -C {n} -cf - . | tar -tvf -",
                   "fi", ""]
    return "\n".join(lignes)


MARQUE = ".genere-par-netbox"


def vider_sortie(sortie):
    """Supprime l'ancienne génération : un fichier périmé serait sinon publié sur les nœuds.

    Ne vide qu'un dossier vide ou portant la marque du générateur, jamais un autre dossier.
    """
    if sortie.exists() and any(sortie.iterdir()):
        if not (sortie / MARQUE).exists():
            sys.exit(f"{sortie} n'est pas un dossier de génération (pas de {MARQUE}) : refus de le vider.")
        shutil.rmtree(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / MARQUE).write_text("Dossier écrit par netbox/outils/generer.py, vidé à chaque génération.\n",
                                 encoding="utf-8")


def generer(m, sortie=None):
    """Retourne {chemin relatif: contenu} et l'écrit dans 'sortie' si fourni."""
    fichiers = {}
    noeuds = [n for n, e in m["equipements"].items() if est_ubuntu(e)]
    for n in noeuds:
        fichiers[f"{n}/99-{n}-netplan.yaml"] = netplan(m, n)
        if reseaux_macvlan(m, n):
            fichiers[f"{n}/creation_vlan.sh"] = creation_vlan(m, n)
    for snom, s in m.get("services", {}).items():
        for n in membres(m, s["cluster"]):
            fichiers[f"{n}/{s['chemin']}/docker-compose.yml"] = compose(m, snom)
    for gnom, g in (m.get("vrrp") or {}).items():
        for n in g["membres"]:
            fichiers[f"{n}/config_cluster.json"] = config_cluster(m, gnom)
    fichiers["matrice_flux.md"] = matrice_flux(m)
    fichiers["topologie.html"] = topologie(m)
    fichiers["publier.sh"] = publier(m, noeuds)
    if sortie:
        vider_sortie(Path(sortie))
        for chemin, contenu in fichiers.items():
            cible = Path(sortie) / chemin
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_text(contenu, encoding="utf-8", newline="\n")
    return fichiers


def main():
    console_utf8()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("source", nargs="?", default=str(Path(__file__).resolve().parents[1] / "donnees" / "sii.yaml"))
    p.add_argument("-o", "--sortie", default=str(Path(__file__).resolve().parents[1] / "genere"))
    args = p.parse_args()
    m = charger(args.source)
    erreurs, _ = valider(m)
    if erreurs:
        sys.exit("Modèle invalide, lancer outils/modele.py pour le détail.")
    fichiers = generer(m, args.sortie)
    for chemin in sorted(fichiers):
        print(f"  {chemin}")
    print(f"{len(fichiers)} fichiers écrits dans {args.sortie}")


if __name__ == "__main__":
    main()
