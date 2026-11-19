"""Compare l'état réel des nœuds (collecte.sh) au modèle (NetBox exporté ou sii.yaml).

    python outils/derive.py collecte/ [donnees/sii.yaml]

Sortie : un écart par ligne. Code retour 1 s'il reste des écarts (INFO ne compte pas).
"""
import ipaddress
import json
import sys
from pathlib import Path

from modele import SOURCE_DEFAUT, charger, console_utf8, est_ubuntu, membres, reseaux_macvlan

ECART, INFO = "ÉCART", "INFO"


def ips_hote(collecte):
    """{interface: {'192.168.10.10/24', ...}} depuis 'ip -j addr'."""
    return {a["ifname"]: {f"{x['local']}/{x['prefixlen']}" for x in a.get("addr_info", []) if x.get("family") == "inet"}
            for a in collecte.get("adresses", [])}


def deriver(m, collectes):
    """collectes : {nom du nœud: contenu JSON de collecte.sh}. Retourne [(niveau, texte)]."""
    sortie = []

    def noter(niveau, noeud, texte):
        sortie.append((niveau, f"{noeud} : {texte}"))

    for noeud, eq in m["equipements"].items():
        if not est_ubuntu(eq):
            continue
        c = collectes.get(noeud)
        if c is None:
            noter(ECART, noeud, "aucune collecte (collecte/<noeud>.json absent)")
            continue
        if c.get("hote") != noeud:
            noter(ECART, noeud, f"le nom d'hôte réel est '{c.get('hote')}'")

        # 1. Réseau de l'hôte
        reel = ips_hote(c)
        vips = {g["vip"] for g in (m.get("vrrp") or {}).values() if noeud in g["membres"]}
        itfs = eq.get("interfaces") or {}
        for inom, itf in itfs.items():
            if inom not in reel:
                noter(ECART, noeud, f"interface {inom} absente")
                continue
            attendu = {itf["ip"]} if itf.get("ip") else set()
            for ip in sorted(attendu - reel[inom]):
                noter(ECART, noeud, f"{inom} : IP {ip} attendue mais absente")
            for ip in sorted(reel[inom] - attendu):
                if ip in vips:
                    noter(INFO, noeud, f"{inom} porte la VIP {ip} : ce nœud est maître VRRP")
                else:
                    noter(ECART, noeud, f"{inom} : IP {ip} présente mais absente du modèle")
        for inom in sorted(reel):
            if inom.startswith("eth") and inom not in itfs:
                noter(ECART, noeud, f"interface {inom} présente mais absente du modèle")

        # 2. Réseaux Docker macvlan
        attendus = reseaux_macvlan(m, noeud)
        vus = set()
        for r in c.get("reseaux", []):
            nom = r["Name"]
            vus.add(nom)
            if nom not in attendus:
                noter(ECART, noeud, f"réseau Docker {nom} présent mais absent du modèle")
                continue
            a = attendus[nom]
            ipam = ((r.get("IPAM") or {}).get("Config") or [{}])[0]
            reel_r = {"parent": (r.get("Options") or {}).get("parent"), "subnet": ipam.get("Subnet"),
                      "gateway": ipam.get("Gateway"), "ip_range": ipam.get("IPRange")}
            for cle, val in a.items():
                if reel_r[cle] != val:
                    noter(ECART, noeud, f"réseau {nom} : {cle} = {reel_r[cle]}, attendu {val}")
        for nom in sorted(set(attendus) - vus):
            noter(ECART, noeud, f"réseau Docker {nom} absent (lancer creation_vlan.sh)")

        # 3. Conteneurs
        services = {s["compose"]["container_name"]: s for s in (m.get("services") or {}).values()
                    if noeud in membres(m, s["cluster"])}
        racine = (eq.get("contexte") or {}).get("racine_projets")
        vus = set()
        for ct in c.get("inspect", []):
            nom = ct["Name"].lstrip("/")
            vus.add(nom)
            s = services.get(nom)
            if s is None:
                noter(ECART, noeud, f"conteneur {nom} présent mais absent du modèle")
                continue
            if ct["Config"]["Image"] != s["compose"]["image"]:
                noter(ECART, noeud, f"{nom} : image {ct['Config']['Image']}, attendu {s['compose']['image']}")
            reseaux = (ct.get("NetworkSettings") or {}).get("Networks") or {}
            for reseau, adresse in (s.get("ip") or {}).items():
                r = reseaux.get(reseau) or {}
                ip = (r.get("IPAMConfig") or {}).get("IPv4Address") or r.get("IPAddress")
                if ip != str(ipaddress.ip_interface(adresse).ip):
                    noter(ECART, noeud, f"{nom} : IP sur {reseau} = {ip or 'aucune'}, attendu {adresse}")
            dossier = (ct["Config"].get("Labels") or {}).get("com.docker.compose.project.working_dir")
            if racine and dossier and dossier != f"{racine}/{s['chemin']}":
                noter(ECART, noeud, f"{nom} : déployé depuis {dossier}, le modèle dit {racine}/{s['chemin']}")
            etat = (ct.get("State") or {}).get("Status")
            if etat != "running" and not s.get("ha"):
                noter(ECART, noeud, f"{nom} : état {etat}")
            elif etat != "running":
                noter(INFO, noeud, f"{nom} : état {etat} (normal sur le nœud passif)")
        for nom in sorted(set(services) - vus):
            s = services[nom]
            noter(INFO if s.get("ha") else ECART, noeud,
                  f"conteneur {nom} absent" + (" (normal sur un nœud jamais passé maître)" if s.get("ha") else ""))
    return sortie


def main():
    console_utf8()
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dossier = Path(sys.argv[1])
    m = charger(sys.argv[2] if len(sys.argv) > 2 else SOURCE_DEFAUT)
    collectes = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(dossier.glob("*.json"))}
    resultats = deriver(m, collectes)
    for niveau, texte in resultats:
        print(f"  [{niveau}] {texte}")
    nb = sum(1 for n, _ in resultats if n == ECART)
    print(f"{nb} écart(s) entre les nœuds et le modèle.")
    sys.exit(1 if nb else 0)


if __name__ == "__main__":
    main()
