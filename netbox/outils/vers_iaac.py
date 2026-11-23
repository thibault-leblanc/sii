"""Synchronise iaac/infrastructure.json (format de l'IaC historique et de son interface web) avec NetBox.

    python outils/vers_iaac.py [donnees/sii.yaml]      # réécrit iaac/infrastructure.json
    python outils/vers_iaac.py --verifier              # code 1 si infrastructure.json n'est pas à jour

Règles :
- NetBox fait foi : tout champ qui vient de NetBox est réécrit à chaque synchronisation ;
- l'IaC peut porter PLUS d'informations : un champ ajouté à la main sur un objet, ou une section entière inconnue
  de NetBox, est conservé tel quel ;
- un objet qui n'existe plus dans NetBox (équipement, service, VLAN) disparaît de l'IaC.
"""
import argparse
import copy
import datetime
import ipaddress
import json
import sys
from pathlib import Path

from generer import flux
from modele import (RACINE_REPO, SOURCE_DEFAUT, charger, clusters_de, cluster_du_vrrp, console_utf8, ip_principale,
                    membres, passerelle, ports_compacts, ports_explicites, valider)

CIBLE = RACINE_REPO / "iaac" / "infrastructure.json"
DEPOT = "https://github.com/thibault-leblanc/sii/tree/main/"
# Types de l'IaC historique (énumération de iaac/schema.json), par type d'équipement NetBox puis par rôle.
TYPES = {"rpi-3b": "raspberry_pi_3b", "rpi-5": "raspberry_pi_5"}
TYPES_PAR_ROLE = {"pare-feu": "pare-feu", "commutateur": "commutateur", "poste-admin": "poste"}


def cle_vlan(vid):
    return f"VLAN{vid}"


def interfaces_physiques(eq):
    sortie = {}
    for nom, itf in (eq.get("interfaces") or {}).items():
        e = {"type": "virtuelle" if itf.get("parent") or itf.get("type") == "virtual" else "physique"}
        if "vlans" in itf:
            e |= {"mode": "trunk", "vlans_autorises": [cle_vlan(v) for v in itf["vlans"]]}
        elif "vlan" in itf:
            e |= {"mode": "access", "vlan_id": cle_vlan(itf["vlan"])}
        if itf.get("ip"):
            e["ip"] = itf["ip"]
        if itf.get("cable"):
            e["liaison_physique"] = itf["cable"]
        if itf.get("parent"):
            e["parent"] = itf["parent"]
        if itf.get("description"):
            e["description"] = itf["description"]
        sortie[nom] = e
    return sortie


def convertir(m):
    """Modèle (export NetBox) -> structure de l'IaC historique, sans les ajouts manuels."""
    services = m.get("services") or {}
    iaac = {"metadonnes": {
        "nom_plateforme": "SII_PLATEFORME",
        "description": "Ontologie IaaC - Système d'Information Industriel. Synchronisée depuis NetBox "
                       "(netbox/outils/vers_iaac.py) ; les champs ajoutés à la main sont conservés.",
        "source_de_verite": "NetBox (export : netbox/donnees/sii.yaml)"}}

    iaac["reseaux_globaux"] = {}
    for vid, v in sorted(m["vlans"].items()):
        iaac["reseaux_globaux"][cle_vlan(vid)] = {
            "nom": v["nom"], "id": vid, "description": v.get("description", ""), "sous_reseau": v["prefixe"],
            **({"passerelle": passerelle(m, v["prefixe"])} if passerelle(m, v["prefixe"]) else {}),
            **({"plage_macvlan": v["plage_macvlan"]} if v.get("plage_macvlan") else {})}

    iaac["clusters"] = {c: {"description": d or "", "membres": membres(m, c)} for c, d in m["clusters"].items()}

    iaac["ressources_physiques"] = {}
    for nom, eq in m["equipements"].items():
        t = m["types"].get(eq["type"], {})
        principale = ip_principale(m, nom)
        e = {"type": TYPES.get(eq["type"]) or TYPES_PAR_ROLE.get(eq["role"], eq["role"]), "nom": nom,
             "role": eq["role"], "fonction": eq.get("description", ""),
             "marque": t.get("fabricant", ""), "modele": t.get("modele", "")}
        if principale:
            e["ip_gestion"] = str(principale.ip)
        if eq.get("plateforme"):
            e["systeme_exploitation"] = m["plateformes"].get(eq["plateforme"], eq["plateforme"])
        if clusters_de(eq):
            e["clusters"] = clusters_de(eq)
            e["charges_logiques_nominales"] = sorted(s for s, v in services.items() if v["cluster"] in clusters_de(eq))
        if eq.get("contexte"):
            e["arborescence_hote"] = eq["contexte"]
        e["interfaces"] = interfaces_physiques(eq)
        if eq.get("ports"):
            e["ports"] = eq["ports"]
        iaac["ressources_physiques"][nom] = e

    iaac["ressources_logiques"] = {}
    for nom, s in services.items():
        e = {"type": "conteneur_docker", "nom": nom, "fonction": s.get("description", ""),
             "cluster": s["cluster"], "hote_parent": membres(m, s["cluster"]), "haute_disponibilite": bool(s.get("ha")),
             "depot_source": DEPOT + s["source"] if s.get("source") else "", "chemin_deploiement": s.get("chemin", "")}
        if s.get("ip"):
            e["interfaces"] = {r: {"type": "macvlan", "vlan_id": cle_vlan(int(r[4:])),
                                   "ip_statique": str(ipaddress.ip_interface(a).ip)}
                               for r, a in s["ip"].items()}
        elif s.get("compose", {}).get("network_mode") == "host":
            e["interfaces"] = {"host-net": {"type": "host", "description": "Réseau de l'hôte"}}
        for cle in ("passerelle", "ports", "fichiers", "amorcage", "compose"):
            if s.get(cle):
                e[cle] = s[cle]
        iaac["ressources_logiques"][nom] = e

    iaac["vrrp"] = {g: {"vrid": v["vrid"], "vip": v["vip"], "interface": v["interface"], "membres": v["membres"],
                        "cluster": cluster_du_vrrp(m, v)} for g, v in (m.get("vrrp") or {}).items()}
    iaac["flux"] = [{k: f[k] for k in ("client", "source", "service", "destination", "proto", "ports", "pare_feu")}
                    for f in sorted(flux(m), key=lambda f: (f["service"], f["client"] or "")) if f["client"]]
    return iaac


# Valeurs NetBox remplacées d'un bloc (une clé retirée dans NetBox ne doit pas survivre dans l'IaC).
ATOMIQUES = {"compose", "ports", "fichiers", "amorcage", "arborescence_hote", "membres", "metadonnes"}


def fusionner(genere, ancien):
    """Valeurs de NetBox prioritaires ; champs et sections ajoutés à la main conservés (objets disparus : retirés)."""
    if not isinstance(genere, dict) or not isinstance(ancien, dict):
        return copy.deepcopy(genere)
    sortie = {}
    for k, v in genere.items():
        sortie[k] = fusionner(v, ancien[k]) if k in ancien and k not in ATOMIQUES else copy.deepcopy(v)
    for k, v in ancien.items():
        if k not in genere and not _objet_de_netbox(genere):
            sortie[k] = copy.deepcopy(v)
    return sortie


def _objet_de_netbox(d):
    """Dictionnaire indexé par nom d'objet NetBox (équipements, services, VLAN...) : un nom absent = objet supprimé."""
    return getattr(d, "_collection", False)


class _Collection(dict):
    _collection = True


def marquer_collections(iaac):
    for section in ("reseaux_globaux", "ressources_physiques", "ressources_logiques", "clusters", "vrrp"):
        iaac[section] = _Collection(iaac[section])
        for obj in iaac[section].values():
            if isinstance(obj.get("interfaces"), dict):
                obj["interfaces"] = _Collection(obj["interfaces"])
    return iaac


def synchroniser(m, ancien):
    nouveau = fusionner(marquer_collections(convertir(m)), ancien or {})
    nouveau = json.loads(json.dumps(nouveau))  # retire les marqueurs de collection
    meta = nouveau["metadonnes"]
    # La date ne change que si le contenu change (sinon chaque synchronisation créerait un diff).
    comparable = {k: v for k, v in nouveau.items() if k != "metadonnes"}
    ancien_comparable = {k: v for k, v in (ancien or {}).items() if k != "metadonnes"}
    date_precedente = (ancien or {}).get("metadonnes", {}).get("derniere_mise_a_jour")
    meta["derniere_mise_a_jour"] = (date_precedente if comparable == ancien_comparable and date_precedente
                                    else datetime.date.today().isoformat())
    return nouveau


def texte(iaac):
    return json.dumps(iaac, indent=2, ensure_ascii=False) + "\n"


def main():
    console_utf8()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("source", nargs="?", default=str(SOURCE_DEFAUT))
    p.add_argument("--verifier", action="store_true", help="ne rien écrire ; code 1 si l'IaC n'est pas à jour")
    p.add_argument("--reinitialiser", action="store_true",
                   help="repartir de NetBox seul, sans conserver l'ancien contenu (première synchronisation)")
    args = p.parse_args()
    m = charger(args.source)
    if valider(m)[0]:
        sys.exit("Modèle invalide, lancer outils/modele.py pour le détail.")
    ancien = json.loads(CIBLE.read_text(encoding="utf-8")) if CIBLE.exists() and not args.reinitialiser else {}
    nouveau = synchroniser(m, ancien)
    if args.verifier:
        a_jour = texte(nouveau) == CIBLE.read_text(encoding="utf-8") if CIBLE.exists() else False
        print(f"iaac/infrastructure.json : {'à jour' if a_jour else 'PAS à jour (lancer outils/vers_iaac.py)'}")
        sys.exit(0 if a_jour else 1)
    CIBLE.write_text(texte(nouveau), encoding="utf-8", newline="\n")
    print(f"Écrit : {CIBLE.relative_to(RACINE_REPO)}")


if __name__ == "__main__":
    main()
