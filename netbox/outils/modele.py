"""Modèle SII : chargement, validation et comparaison du fichier sii.yaml.

Ce module ne parle pas à NetBox : tout ce qu'il fait fonctionne hors ligne.

    python outils/modele.py donnees/sii.yaml     # valide le fichier et liste les points à vérifier
"""
import copy
import ipaddress
import re
import sys
import unicodedata
from pathlib import Path

import yaml

INTERFACE_PHYSIQUE = "1000base-t"
ROLE_CONTENEUR = "conteneur"
DOSSIER_NETBOX = Path(__file__).resolve().parents[1]
RACINE_REPO = DOSSIER_NETBOX.parent
SOURCE_DEFAUT = DOSSIER_NETBOX / "donnees" / "sii.yaml"


def console_utf8():
    """Évite les UnicodeEncodeError quand la sortie Windows est redirigée."""
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")


def charger(chemin=SOURCE_DEFAUT):
    with open(chemin, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ecrire_yaml(donnees, chemin=None, entete=""):
    texte = entete + yaml.safe_dump(donnees, sort_keys=False, allow_unicode=True, width=120)
    if chemin:
        Path(chemin).write_text(texte, encoding="utf-8")
    return texte


def slugifier(texte):
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


# --- Ports -----------------------------------------------------------------

def ports_explicites(ports):
    """[21, '21000-21002'] -> [21, 21000, 21001, 21002]"""
    sortie = set()
    for p in ports or []:
        if isinstance(p, str) and "-" in p:
            debut, fin = (int(x) for x in p.split("-"))
            sortie.update(range(debut, fin + 1))
        else:
            sortie.add(int(p))
    return sorted(sortie)


def ports_compacts(ports):
    """[21, 21000, 21001, 21002] -> [21, '21000-21002'] (plages de 3 ports ou plus)."""
    sortie, ports = [], sorted(set(ports))
    i = 0
    while i < len(ports):
        j = i
        while j + 1 < len(ports) and ports[j + 1] == ports[j] + 1:
            j += 1
        if j - i >= 2:
            sortie.append(f"{ports[i]}-{ports[j]}")
        else:
            sortie.extend(ports[i:j + 1])
        i = j + 1
    return sortie


# --- Lecture du modèle -----------------------------------------------------

def vid_de_reseau(nom_reseau):
    """'vlan20' -> 20 (nom des réseaux Docker macvlan et des interfaces de conteneur)."""
    m = re.fullmatch(r"vlan(\d+)", nom_reseau)
    return int(m.group(1)) if m else None


def ips_de(m, proprietaire):
    """Adresses (ip_interface) d'un équipement ou d'un service, dans l'ordre de déclaration."""
    if proprietaire in m.get("equipements", {}):
        itfs = m["equipements"][proprietaire].get("interfaces") or {}
        return [ipaddress.ip_interface(i["ip"]) for i in itfs.values() if i.get("ip")]
    s = m.get("services", {}).get(proprietaire, {})
    return [ipaddress.ip_interface(ip) for ip in (s.get("ip") or {}).values()]


def ip_principale(m, proprietaire):
    if proprietaire in m.get("equipements", {}):
        for itf in (m["equipements"][proprietaire].get("interfaces") or {}).values():
            if itf.get("principale"):
                return ipaddress.ip_interface(itf["ip"])
    ips = ips_de(m, proprietaire)
    return ips[0] if ips else None


def passerelle(m, reseau):
    """La passerelle d'un réseau est l'IP du pare-feu dans ce réseau."""
    reseau = ipaddress.ip_network(reseau)
    for eq in m.get("equipements", {}).values():
        if eq.get("role") != "pare-feu":
            continue
        for itf in (eq.get("interfaces") or {}).values():
            if itf.get("ip") and ipaddress.ip_interface(itf["ip"]).network == reseau:
                return str(ipaddress.ip_interface(itf["ip"]).ip)
    return None


def membres(m, cluster):
    return sorted(n for n, e in m.get("equipements", {}).items() if e.get("cluster") == cluster)


def est_ubuntu(eq):
    return str(eq.get("plateforme", "")).startswith("ubuntu")


def reseaux_macvlan(m, noeud):
    """Réseaux Docker macvlan attendus sur un nœud : un par sous-interface VLAN qui a une plage macvlan."""
    sortie = {}
    for inom, itf in (m["equipements"][noeud].get("interfaces") or {}).items():
        v = m["vlans"].get(itf.get("vlan"))
        if itf.get("parent") and v and v.get("plage_macvlan"):
            sortie[f"vlan{itf['vlan']}"] = {
                "parent": inom,
                "subnet": v["prefixe"],
                "gateway": passerelle(m, v["prefixe"]),
                "ip_range": v["plage_macvlan"],
            }
    return sortie


# --- Validation ------------------------------------------------------------

def valider(m, racine_repo=RACINE_REPO):
    """Retourne (erreurs, avertissements). Une erreur bloque l'import."""
    err, avert = [], []
    vlans = m.get("vlans") or {}
    equipements = m.get("equipements") or {}
    services = m.get("services") or {}
    roles = m.get("roles") or {}

    for cle in ("site", "dns", "vlans", "roles", "types", "clusters", "equipements"):
        if not m.get(cle):
            err.append(f"section '{cle}' absente ou vide")
    if ROLE_CONTENEUR not in roles or not roles[ROLE_CONTENEUR].get("vm"):
        err.append(f"le rôle '{ROLE_CONTENEUR}' (vm: true) est requis pour les services")
    for nom in set(equipements) & set(services):
        err.append(f"'{nom}' est à la fois un équipement et un service")

    for vid, v in vlans.items():
        if not isinstance(vid, int):
            err.append(f"VLAN '{vid}' : la clé doit être un numéro")
            continue
        try:
            reseau = ipaddress.ip_network(v["prefixe"])
            if v.get("plage_macvlan") and not ipaddress.ip_network(v["plage_macvlan"]).subnet_of(reseau):
                err.append(f"VLAN {vid} : plage macvlan hors du préfixe")
        except (KeyError, ValueError) as e:
            err.append(f"VLAN {vid} : préfixe ou plage invalide ({e})")
            continue
        if not passerelle(m, v["prefixe"]):
            avert.append(f"VLAN {vid} : aucune IP de pare-feu dans {v['prefixe']} (pas de passerelle)")

    vues = {}  # adresse -> propriétaire, pour l'unicité

    def noter_ip(adresse, ou, vlan=None):
        try:
            ip = ipaddress.ip_interface(adresse)
        except ValueError:
            err.append(f"{ou} : IP invalide '{adresse}'")
            return None
        if ip.network.prefixlen == ip.max_prefixlen:
            err.append(f"{ou} : IP '{adresse}' sans masque (ex. /24)")
        if str(ip.ip) in vues:
            err.append(f"{ou} : IP {ip.ip} déjà utilisée par {vues[str(ip.ip)]}")
        vues[str(ip.ip)] = ou
        if vlan in vlans:
            if ip.network != ipaddress.ip_network(vlans[vlan]["prefixe"]):
                err.append(f"{ou} : IP {adresse} hors du préfixe du VLAN {vlan}")
            plage = vlans[vlan].get("plage_macvlan")
            if plage and ip.ip in ipaddress.ip_network(plage):
                avert.append(f"{ou} : IP statique {ip.ip} dans la plage macvlan {plage} (audit H9)")
        return ip

    for nom, eq in equipements.items():
        ou = f"équipement {nom}"
        for cle, table in (("type", "types"), ("role", "roles"), ("plateforme", "plateformes"), ("cluster", "clusters")):
            if eq.get(cle) is not None and eq[cle] not in (m.get(table) or {}):
                err.append(f"{ou} : {cle} '{eq[cle]}' inconnu dans '{table}'")
        itfs = eq.get("interfaces") or {}
        principales = [i for i, itf in itfs.items() if itf.get("principale")]
        if len(principales) > 1:
            err.append(f"{ou} : plusieurs interfaces principales {principales}")
        for inom, itf in itfs.items():
            oui = f"{ou}/{inom}"
            if itf.get("parent") and itf["parent"] not in itfs:
                err.append(f"{oui} : parent '{itf['parent']}' inconnu")
            if itf.get("parent") and itf.get("vlan") and inom != f"{itf['parent']}.{itf['vlan']}":
                avert.append(f"{oui} : le nom ne suit pas <parent>.<vlan>")
            for vid in ([itf["vlan"]] if "vlan" in itf else []) + list(itf.get("vlans") or []):
                if vid not in vlans:
                    err.append(f"{oui} : VLAN {vid} inconnu")
            if "vlan" in itf and "vlans" in itf:
                err.append(f"{oui} : 'vlan' (accès) et 'vlans' (trunk) sont exclusifs")
            if itf.get("ip"):
                noter_ip(itf["ip"], oui, itf.get("vlan"))
            if itf.get("principale") and not itf.get("ip"):
                err.append(f"{oui} : interface principale sans IP")
            if itf.get("cable"):
                pair, _, pitf = itf["cable"].partition("/")
                if pair not in equipements or pitf not in (equipements[pair].get("interfaces") or {}):
                    err.append(f"{oui} : câble vers '{itf['cable']}' inconnu")
                elif eq.get("role") == "commutateur":
                    err.append(f"{oui} : déclarer le câble côté équipement, pas côté commutateur")
                elif equipements[pair].get("role") != "commutateur" and pair < nom:
                    err.append(f"{oui} : câble entre deux équipements à déclarer côté '{pair}' (ordre alphabétique)")
        if eq.get("cluster") and not est_ubuntu(eq):
            avert.append(f"{ou} : membre d'un cluster sans plateforme Ubuntu (pas de netplan généré)")

    cables = {}
    for nom, eq in equipements.items():
        for inom, itf in (eq.get("interfaces") or {}).items():
            if itf.get("cable"):
                for bout in (f"{nom}/{inom}", itf["cable"]):
                    if bout in cables:
                        err.append(f"interface {bout} câblée deux fois ({cables[bout]})")
                    cables[bout] = f"{nom}/{inom}"

    for gnom, g in (m.get("vrrp") or {}).items():
        ou = f"vrrp {gnom}"
        vip = noter_ip(g.get("vip", ""), ou)
        for dnom in g.get("membres") or {}:
            itf = (equipements.get(dnom, {}).get("interfaces") or {}).get(g.get("interface"))
            if itf is None:
                err.append(f"{ou} : interface {dnom}/{g.get('interface')} inconnue")
            elif vip and itf.get("ip") and ipaddress.ip_interface(itf["ip"]).network != vip.network:
                err.append(f"{ou} : VIP hors du réseau de {dnom}/{g['interface']}")
        clusters = {equipements.get(d, {}).get("cluster") for d in g.get("membres") or {}}
        if len(clusters) != 1:
            err.append(f"{ou} : les membres doivent appartenir au même cluster ({clusters})")

    for snom, s in services.items():
        ou = f"service {snom}"
        if s.get("cluster") not in (m.get("clusters") or {}):
            err.append(f"{ou} : cluster '{s.get('cluster')}' inconnu")
        elif not membres(m, s["cluster"]):
            err.append(f"{ou} : le cluster '{s['cluster']}' n'a aucun membre")
        if not s.get("chemin"):
            err.append(f"{ou} : 'chemin' (dossier de déploiement) manquant")
        c = s.get("compose") or {}
        for cle in ("service", "image", "container_name"):
            if not c.get(cle):
                err.append(f"{ou} : compose.{cle} manquant")
        if "networks" in c:
            err.append(f"{ou} : ne pas mettre 'networks' dans compose, il est généré depuis 'ip'")
        if s.get("ha") and c.get("restart", "no") != "no":
            avert.append(f"{ou} : service HA avec restart '{c['restart']}' : Docker le relancera au démarrage "
                         "du nœud, même passif (doublon d'IP, audit n°3). Mettre restart: \"no\"")
        if s.get("source") and not (Path(racine_repo) / s["source"]).is_dir():
            avert.append(f"{ou} : dossier source '{s['source']}' introuvable dans le repo")
        for reseau, adresse in (s.get("ip") or {}).items():
            vid = vid_de_reseau(reseau)
            if vid not in vlans:
                err.append(f"{ou} : interface '{reseau}' doit s'appeler vlan<numéro> d'un VLAN connu")
            noter_ip(adresse, f"{ou}/{reseau}", vid)

    proprietaires = {**{n: e.get("ports") for n, e in equipements.items()},
                     **{n: s.get("ports") for n, s in services.items()}}
    for proprio, ports in proprietaires.items():
        for pnom, p in (ports or {}).items():
            ou = f"{proprio}/port {pnom}"
            if p.get("proto") not in ("tcp", "udp"):
                err.append(f"{ou} : proto doit être tcp ou udp")
            try:
                if not ports_explicites(p.get("ports")):
                    err.append(f"{ou} : aucun port")
            except ValueError:
                err.append(f"{ou} : ports invalides {p.get('ports')}")
            for client in p.get("clients") or []:
                if client not in proprietaires:
                    err.append(f"{ou} : client '{client}' inconnu")
            if p.get("ip") and p["ip"] not in [str(i) for i in ips_de(m, proprio)]:
                err.append(f"{ou} : ip {p['ip']} n'appartient pas à {proprio}")

    avert.extend(f"À vérifier : {x}" for x in m.get("a_verifier") or [])
    return err, avert


# --- Comparaison -----------------------------------------------------------

def normaliser(m):
    """Forme canonique pour comparer deux modèles (source et export NetBox)."""
    m = copy.deepcopy(m)
    m.pop("a_verifier", None)

    def nettoyer(x):
        if isinstance(x, dict):
            sortie = {}
            for k, v in x.items():
                if k == "ports" and isinstance(v, list):
                    v = ports_explicites(v)
                v = nettoyer(v)
                if v not in (None, "", [], {}, False):
                    sortie[k] = v
            return sortie
        if isinstance(x, list):
            x = [nettoyer(v) for v in x]
            return sorted(x, key=str) if all(not isinstance(v, (dict, list)) for v in x) else x
        return x

    return nettoyer(m)


def differences(a, b, chemin=""):
    """Liste lisible des écarts entre deux structures (a = attendu, b = obtenu)."""
    if isinstance(a, dict) and isinstance(b, dict):
        sortie = []
        for k in list(a) + [k for k in b if k not in a]:
            ici = f"{chemin}.{k}" if chemin else str(k)
            if k not in b:
                sortie.append(f"{ici} : absent de l'export")
            elif k not in a:
                sortie.append(f"{ici} : en trop dans l'export ({b[k]!r})")
            else:
                sortie.extend(differences(a[k], b[k], ici))
        return sortie
    return [] if a == b else [f"{chemin} : attendu {a!r}, obtenu {b!r}"]


def main():
    console_utf8()
    chemin = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    erreurs, avertissements = valider(charger(chemin))
    for a in avertissements:
        print(f"  ! {a}")
    for e in erreurs:
        print(f"  ✗ {e}")
    print(f"{chemin} : {len(erreurs)} erreur(s), {len(avertissements)} avertissement(s)")
    sys.exit(1 if erreurs else 0)


if __name__ == "__main__":
    main()
