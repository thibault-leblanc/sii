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
import os
import shutil
import sys
from pathlib import Path

from modele import (RACINE_REPO, charger, clusters_de, cluster_du_vrrp, console_utf8, ecrire_yaml, ip_principale,
                    ips_de, membres, passerelle, ports_compacts, ports_explicites, reseaux_macvlan, est_ubuntu,
                    valider, vid_de_reseau)

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


ORDRE_COMPOSE = ["image", "container_name", "restart", "network_mode", "privileged", "ports", "environment", "volumes"]


def compose(m, snom):
    s = m["services"][snom]
    corps = dict(s["compose"])
    cle = corps.pop("service")
    # Ordre fixe : NetBox renvoie les clés JSON triées à sa façon, la sortie doit rester stable.
    corps = {k: corps[k] for k in sorted(corps, key=lambda k: (ORDRE_COMPOSE + [k]).index(k))}
    ips = s.get("ip") or {}
    if ips:
        corps["networks"] = {r: {"ipv4_address": str(ipaddress.ip_interface(a).ip)} for r, a in ips.items()}
        if s.get("passerelle"):
            # Conteneur à plusieurs réseaux : Docker ne pose qu'une route par défaut. Sans choix explicite, l'automate
            # répondait par le VLAN20 à une demande arrivée par le VLAN30 (routage asymétrique, rejet au pare-feu).
            corps["networks"][s["passerelle"]]["gw_priority"] = 1
    # Nom de projet explicite : sinon Compose prend le nom du dossier, et api/rincage et simulation/rincage
    # partagent le projet « rincage » (chacun voit l'autre comme orphelin, --remove-orphans le supprimerait).
    doc = {"name": snom, "services": {cle: corps}}
    if ips:
        doc["networks"] = {r: {"external": True} for r in ips}
    return ecrire_yaml(doc, entete=ENTETE)


def config_cluster(m, gnom):
    """Format attendu par l'agent HA actuel (configurations/conteneurs/cluster/Dockerfile)."""
    g = m["vrrp"][gnom]
    premier = next(iter(g["membres"]))
    cluster = cluster_du_vrrp(m, g)
    # Sous-interface hôte de chaque VLAN (identique sur les membres) : l'agent y vérifie par ARP qu'une IP de
    # service ne répond plus ailleurs avant de démarrer le service (audit H6).
    sous_itf = {itf["vlan"]: n for n, itf in (m["equipements"][premier].get("interfaces") or {}).items()
                if itf.get("parent") and itf.get("vlan")}
    surveilles = {
        n: {"nom_conteneur": s["compose"]["container_name"], "chemin_compose": s["chemin"],
            **{f"priorite_{d}": p for d, p in g["membres"].items()},
            "adresses": [{"ip": str(ipaddress.ip_interface(a).ip), "interface": sous_itf[vid_de_reseau(r)]}
                         for r, a in sorted((s.get("ip") or {}).items())]}
        for n, s in sorted(m["services"].items()) if s.get("ha") and s["cluster"] == cluster
    }
    conf = {"vip_admin": str(ipaddress.ip_interface(g["vip"]).ip), "vrid": g["vrid"],
            "interface_heartbeat": g["interface"], "services_surveilles": surveilles}
    return json.dumps(conf, indent=2, ensure_ascii=False) + "\n"


def hotes(m, proprio):
    """Service publié sur l'hôte (sans IP macvlan) : il répond sur l'IP principale des nœuds de son cluster."""
    s = m.get("services", {}).get(proprio)
    return [ip for n in membres(m, s["cluster"]) if (ip := ip_principale(m, n))] if s else []


def flux(m):
    """Une ligne par (client, service) : IP source, destination et besoin d'une règle de pare-feu."""
    proprietaires = {**{n: e.get("ports") for n, e in m["equipements"].items()},
                     **{n: s.get("ports") for n, s in m.get("services", {}).items()}}
    lignes = []
    for proprio, ports in proprietaires.items():
        for pnom, p in (ports or {}).items():
            cibles = [ipaddress.ip_interface(p["ip"])] if p.get("ip") else ips_de(m, proprio) or hotes(m, proprio)
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
        for c in clusters_de(eq):
            lien("cluster", nom, f"cluster:{c}", dashes=True, color="#a78bfa")
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


def publier(m, noeuds, amorcages=(), dossier_noeuds="../../configurations/machines"):
    exclure = f"--exclude=README.md --exclude={MARQUE}"  # la fiche et la marque restent dans le repo
    lignes = ["#!/bin/sh", ENTETE.strip(),
              "# Copie configurations/machines/<noeud>/ dans le dossier personnel de chaque nœud, par SSH",
              "# (compte = nom du nœud), puis l'amorçage (fichiers absents seulement).",
              "# Sans option : affiche seulement ce qui serait copié.  Pour copier : sh publier.sh --appliquer",
              "# Les fichiers remplacés sont gardés à côté avec le suffixe ~1~, ~2~... (GNU tar --backup).",
              "set -e", 'cd "$(dirname "$0")"', ""]
    for n in noeuds:
        ip = ip_principale(m, n).ip
        source = f"{dossier_noeuds}/{n}"
        lignes += [f'echo "== {n} ({ip})"',
                   'if [ "$1" = "--appliquer" ]; then',
                   # --no-overwrite-dir : ne pas changer les droits de ~ (sshd refuserait les clés)
                   f"  tar -C {source} {exclure} -cf - . | ssh {n}@{ip} 'tar -C ~ --no-overwrite-dir --backup=numbered -xvf -'",
                   "else",
                   f"  tar -C {source} {exclure} -cf - . | tar -tvf -",
                   "fi"]
        if n in amorcages:
            # Amorçage : déposé seulement là où rien n'existe encore (jamais d'écrasement de l'état d'exécution).
            lignes += [f'echo "== {n} : amorçage (fichiers absents seulement)"',
                       'if [ "$1" = "--appliquer" ]; then',
                       # --skip-old-files laisse intact tout ce qui existe (fichiers et dossiers, dont ~) ;
                       # GNU tar refuse de le combiner avec --no-overwrite-dir.
                       f"  tar -C {n}.amorcage -cf - . | ssh {n}@{ip} 'tar -C ~ --skip-old-files -xvf -'",
                       "else",
                       f"  tar -C {n}.amorcage -cf - . | tar -tvf -",
                       "fi"]
        lignes.append("")
    return "\n".join(lignes)


DESTINATIONS = {
    "creation_vlan.sh": "`~/creation_vlan.sh` : réseaux Docker macvlan, à lancer une fois (relançable)",
    "config_cluster.json": "`~/config_cluster.json` : lu par l'agent HA",
}


def fiche(m, noeud, chemins):
    """README du dossier d'un nœud : ce qui y tourne, d'où vient chaque fichier, ce qui reste manuel."""
    eq = m["equipements"][noeud]
    t = m["types"].get(eq["type"], {})
    services = sorted((n, s) for n, s in (m.get("services") or {}).items() if noeud in membres(m, s["cluster"]))
    l = [f"# {noeud}", "",
         "> Dossier **généré** par `netbox/outils/generer.py` depuis NetBox : ne pas le modifier à la main.",
         "> Modifier NetBox, puis `python netbox/outils/synchro.py` ; publier avec `sh netbox/genere/publier.sh`.", "",
         "| | |", "|---|---|",
         f"| Rôle | {m['roles'][eq['role']]['nom']} : {eq.get('description', '')} |",
         f"| Matériel | {t.get('modele', '') if t.get('modele', '').startswith(t.get('fabricant', '')) else (t.get('fabricant', '') + ' ' + t.get('modele', '')).strip()} |",
         f"| Système | {m.get('plateformes', {}).get(eq.get('plateforme'), '')} |",
         f"| Clusters | {', '.join(clusters_de(eq))} |",
         f"| Accès | `ssh {noeud}@{ip_principale(m, noeud).ip}` |"]
    for g, v in (m.get("vrrp") or {}).items():
        if noeud in v["membres"]:
            l.append(f"| Haute disponibilité | groupe VRRP `{g}` (VRID {v['vrid']}, VIP {v['vip']}), "
                     f"priorité {v['membres'][noeud]} |")
    l += ["", "## Réseau", "", "| Interface | VLAN | IP | Câble |", "|---|---|---|---|"]
    for i, itf in (eq.get("interfaces") or {}).items():
        vlan = f"trunk {', '.join(map(str, itf['vlans']))}" if itf.get("vlans") else str(itf.get("vlan", ""))
        l.append(f"| `{i}` | {vlan} | {itf.get('ip', '')} | {itf.get('cable', '')} |")
    l += ["", "## Services", "", "| Service | Dossier | IP | Démarrage | Image |", "|---|---|---|---|---|"]
    for n, s in services:
        demarrage = "agent HA, sur le maître seulement" if s.get("ha") else \
            ("Docker, réseau de l'hôte" if s["compose"].get("network_mode") == "host" else "Docker, toujours")
        ips = ", ".join(a.split("/")[0] for a in (s.get("ip") or {}).values())
        l.append(f"| `{n}` ({s['cluster']}) | `~/{s['chemin']}` | {ips} | {demarrage} | `{s['compose']['image']}` |")
    l += ["", "## Fichiers de ce dossier", "", "| Fichier | Destination sur le nœud |", "|---|---|"]
    for c in chemins:
        nom = c.split("/")[-1]
        if nom.endswith("-netplan.yaml"):
            dest = "`/etc/netplan/` : `sudo install -m 600 ~/" + nom + " /etc/netplan/ && sudo netplan try`"
        else:
            dest = DESTINATIONS.get(c, f"`~/{c}`")
        l.append(f"| `{c}` | {dest} |")
    amorces = [(n, d, src) for n, s in services for d, src in (s.get("amorcage") or {}).items()]
    if amorces:
        l += ["", "Données **amorcées** (déposées seulement si absentes, jamais écrasées) :"]
        l += [f"- `~/{(m['services'][n]['chemin'])}/{d}` depuis `{src}`" for n, d, src in amorces]
    l += ["", "## Hors NetBox (à faire ou vérifier à la main)", "",
          "- Clé SSH du poste d'administration dans `~/.ssh/authorized_keys` ; compte et nom d'hôte = `" + noeud + "`.",
          "- Docker installé (`configurations/machines/installation_docker.sh`), mises à jour automatiques "
          "désactivées (`configurations/machines/apt/`).",
          "- Images dans `~/images` (`configurations/images/`, chargées par `docker load` ou par l'agent HA)."]
    # Clés de services clients venant d'autres nœuds (ex. agents rsync de pi51) : une ligne par nœud d'origine.
    clients_par_hote = {}
    for p in (eq.get("ports") or {}).values():
        for client in p.get("clients") or []:
            if client in (m.get("services") or {}):
                for hote in membres(m, m["services"][client]["cluster"]):
                    clients_par_hote.setdefault(hote, set()).add(client)
    for hote, clients in sorted(clients_par_hote.items()):
        l.append(f"- Clé publique de `{hote}` (`~/.ssh/id_rsa.pub`, utilisée par {', '.join(f'`{c}`' for c in sorted(clients))}) "
                 "dans `~/.ssh/authorized_keys`.")
    cle_privee = [n for n, s in services if any("/root/.ssh/id_rsa" in v for v in s["compose"].get("volumes") or [])]
    if cle_privee:
        l.append(f"- `~/.ssh/id_rsa` : clé privée de synchronisation, montée en lecture seule par "
                 f"{', '.join(f'`{n}`' for n in cle_privee)}.")
    for n, s in services:
        for e in s["compose"].get("environment") or []:
            if "${" in e:
                l.append(f"- `~/{s['chemin']}/.env` : `{e.split('=', 1)[0]}=…` (secret, droits 600, jamais versionné).")
        if s.get("ha"):
            l.append(f"- `{n}` : conteneur créé d'avance (`cd ~/{s['chemin']} && docker compose create`), "
                     "jamais `up` : c'est l'agent HA qui le démarre.")
    return "\n".join(l) + "\n"


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


MACHINES = RACINE_REPO / "configurations" / "machines"


def lire_pour_deploiement(source):
    """Fichier du repo à déployer : texte normalisé en LF (une copie de travail Windows peut être en CRLF),
    binaire (ex. base FUXA) laissé intact."""
    contenu = (RACINE_REPO / source).read_bytes()
    return contenu if b"\0" in contenu else contenu.replace(b"\r\n", b"\n")


def ecrire(fichiers, dossier):
    vider_sortie(dossier)
    for chemin, contenu in fichiers.items():
        cible = dossier / chemin
        cible.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contenu, bytes):
            cible.write_bytes(contenu)
        else:
            cible.write_text(contenu, encoding="utf-8", newline="\n")


def generer(m, sortie=None, machines=None):
    """Retourne {chemin relatif: contenu}.

    Si fournis : les fichiers de chaque nœud vont dans machines/<noeud>/ (versionné dans le repo), le reste
    (matrice de flux, topologie, publier.sh, amorçage) dans sortie/ (netbox/genere, hors git).
    """
    fichiers = {}
    noeuds = [n for n, e in m["equipements"].items() if est_ubuntu(e)]
    for n in noeuds:
        fichiers[f"{n}/99-{n}-netplan.yaml"] = netplan(m, n)
        if reseaux_macvlan(m, n):
            fichiers[f"{n}/creation_vlan.sh"] = creation_vlan(m, n)
    amorcages = set()
    for snom, s in m.get("services", {}).items():
        for n in membres(m, s["cluster"]):
            fichiers[f"{n}/{s['chemin']}/docker-compose.yml"] = compose(m, snom)
            # Configurations versionnées dans le repo, déployées à côté du compose (référencées dans NetBox).
            for dest, source in (s.get("fichiers") or {}).items():
                fichiers[f"{n}/{s['chemin']}/{dest}"] = lire_pour_deploiement(source)
            for dest, source in (s.get("amorcage") or {}).items():
                fichiers[f"{n}.amorcage/{s['chemin']}/{dest}"] = lire_pour_deploiement(source)
                amorcages.add(n)
    for gnom, g in (m.get("vrrp") or {}).items():
        for n in g["membres"]:
            fichiers[f"{n}/config_cluster.json"] = config_cluster(m, gnom)
    for n in noeuds:
        fichiers[f"{n}/README.md"] = fiche(m, n, sorted(k[len(n) + 1:] for k in fichiers if k.startswith(f"{n}/")))
    fichiers["matrice_flux.md"] = matrice_flux(m)
    fichiers["topologie.html"] = topologie(m)
    try:
        relatif = os.path.relpath(machines or MACHINES, sortie or RACINE_REPO / "netbox" / "genere").replace("\\", "/")
    except ValueError:  # lecteurs différents sous Windows : chemin absolu
        relatif = Path(machines or MACHINES).resolve().as_posix()
    fichiers["publier.sh"] = publier(m, noeuds, amorcages, relatif)
    if sortie:
        ecrire({k: v for k, v in fichiers.items() if k.split("/")[0] not in noeuds}, Path(sortie))
    if machines:
        for n in noeuds:
            ecrire({k[len(n) + 1:]: v for k, v in fichiers.items() if k.startswith(f"{n}/")}, Path(machines) / n)
    return fichiers


def main():
    console_utf8()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("source", nargs="?", default=str(Path(__file__).resolve().parents[1] / "donnees" / "sii.yaml"))
    p.add_argument("-o", "--sortie", default=str(Path(__file__).resolve().parents[1] / "genere"),
                   help="matrice, topologie, publier.sh, amorçage (hors git)")
    p.add_argument("--machines", default=str(MACHINES), help="dossiers des nœuds (versionnés)")
    args = p.parse_args()
    m = charger(args.source)
    erreurs, _ = valider(m)
    if erreurs:
        sys.exit("Modèle invalide, lancer outils/modele.py pour le détail.")
    fichiers = generer(m, args.sortie, args.machines)
    for chemin in sorted(fichiers):
        print(f"  {chemin}")
    print(f"{len(fichiers)} fichiers écrits ({args.machines}/<noeud>/ et {args.sortie})")


if __name__ == "__main__":
    main()
