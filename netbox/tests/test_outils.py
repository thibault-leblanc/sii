"""Tests hors ligne (sans NetBox) : python -m unittest discover -s tests   (depuis netbox/)"""
import copy
import json
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outils"))

from derive import ECART, deriver  # noqa: E402
from generer import flux, generer  # noqa: E402
from modele import (charger, differences, normaliser, ports_compacts,  # noqa: E402
                    ports_explicites, reseaux_macvlan, valider, clusters_de)



def lire_yaml(texte_ou_chemin):
    texte = Path(texte_ou_chemin).read_text(encoding="utf-8") if isinstance(texte_ou_chemin, Path) else texte_ou_chemin
    return yaml.safe_load(texte)


class TestModele(unittest.TestCase):
    def setUp(self):
        self.m = charger()

    def test_source_valide(self):
        erreurs, _ = valider(self.m)
        self.assertEqual(erreurs, [])

    def test_ip_en_double_detectee(self):
        self.m["services"]["sim-rincage"]["ip"]["vlan20"] = "192.168.20.20/24"
        erreurs, _ = valider(self.m)
        self.assertTrue(any("déjà utilisée" in e for e in erreurs), erreurs)

    def test_vlan_inconnu_detecte(self):
        self.m["equipements"]["pi31"]["interfaces"]["eth0.20"]["vlan"] = 99
        erreurs, _ = valider(self.m)
        self.assertTrue(any("VLAN 99 inconnu" in e for e in erreurs), erreurs)

    def test_client_inconnu_detecte(self):
        self.m["services"]["sim-rincage"]["ports"]["modbus"]["clients"].append("fantome")
        erreurs, _ = valider(self.m)
        self.assertTrue(any("'fantome' inconnu" in e for e in erreurs), erreurs)

    def test_ports(self):
        self.assertEqual(ports_explicites([21, "21000-21002"]), [21, 21000, 21001, 21002])
        self.assertEqual(ports_compacts([21, 22, 21000, 21001, 21002]), [21, 22, "21000-21002"])

    def test_normaliser_ignore_forme(self):
        b = copy.deepcopy(self.m)
        b.pop("a_verifier")
        b["services"]["donnees-vlan-20"]["ports"]["ftp"]["ports"] = ports_explicites([21, "21000-21010"])
        b["equipements"]["pi31"]["ports"]["ssh"]["clients"].reverse()
        self.assertEqual(differences(normaliser(self.m), normaliser(b)), [])

    def test_normaliser_voit_un_vrai_ecart(self):
        b = copy.deepcopy(self.m)
        b["vrrp"]["coeur-sii"]["membres"]["pi32"] = 80
        self.assertEqual(differences(normaliser(self.m), normaliser(b)),
                         ["vrrp.coeur-sii.membres.pi32 : attendu 90, obtenu 80"])


class TestGeneration(unittest.TestCase):
    """Ce que le générateur doit produire.

    Valeurs relevées sur la plateforme le 2026-11-22 (derive.py : 0 écart). Les copies manuelles qui servaient
    de référence dans configurations/ ont été retirées : elles sont générées depuis NetBox.
    """

    @classmethod
    def setUpClass(cls):
        cls.m = charger()
        cls.f = generer(cls.m)

    def test_netplan(self):
        for n, ip in (("pi31", "192.168.10.10/24"), ("pi32", "192.168.10.11/24"), ("pi51", "192.168.10.12/24")):
            with self.subTest(noeud=n):
                reseau = lire_yaml(self.f[f"{n}/99-{n}-netplan.yaml"])["network"]
                self.assertEqual(reseau["ethernets"], {"eth0": {"dhcp4": False, "dhcp6": False}})
                self.assertEqual(reseau["vlans"]["eth0.10"], {
                    "id": 10, "link": "eth0", "dhcp4": False, "addresses": [ip],
                    "routes": [{"to": "default", "via": "192.168.10.1"}],  # route sur l'interface virtuelle (I2)
                    "nameservers": {"addresses": ["1.1.1.1", "8.8.8.8"]}})
                self.assertEqual(reseau["vlans"]["eth0.20"], {"id": 20, "link": "eth0"})  # pas d'IP : conteneurs
                self.assertEqual(reseau["vlans"]["eth0.30"], {"id": 30, "link": "eth0"})

    def test_compose_automate(self):
        doc = lire_yaml(self.f["pi31/api/rincage/docker-compose.yml"])
        self.assertEqual(doc["services"]["api_rincage"], {
            "image": "api-rincage-image:latest", "container_name": "api-rincage", "restart": "no",
            "volumes": ["./config_api.json:/app/config_api.json"],
            "networks": {"vlan20": {"ipv4_address": "192.168.20.20"}, "vlan30": {"ipv4_address": "192.168.30.20"}}})
        self.assertEqual(doc["networks"], {"vlan20": {"external": True}, "vlan30": {"external": True}})

    def test_compose_agent_ha(self):
        s = lire_yaml(self.f["pi32/ha-cluster/docker-compose.yml"])["services"]["ha-cluster"]
        self.assertEqual((s["network_mode"], s["privileged"], s["stop_grace_period"]), ("host", True, "30s"))
        self.assertIn("../:/config:ro", s["volumes"])
        self.assertIn("../.agent-ha:/etat", s["volumes"])  # marques d'images chargées, persistantes
        self.assertNotIn("networks", s)

    def test_noms_de_projet_compose_uniques(self):
        noms = {lire_yaml(c)["name"] for p, c in self.f.items() if p.startswith("pi31/") and p.endswith("compose.yml")}
        self.assertEqual(noms, {"api-rincage", "sim-rincage", "ha-cluster"})

    def test_compose_ftp_sans_secret(self):
        s = lire_yaml(self.f["pi51/donnees-vlan-20/docker-compose.yml"])["services"]["donnees-vlan-20"]
        self.assertEqual(s["volumes"], ["/home/pi51/donnees/vlan20:/partage"])
        self.assertEqual(s["networks"], {"vlan20": {"ipv4_address": "192.168.20.30"}})
        self.assertIn("FTP_PASS=${FTP_PASS:?definir FTP_PASS dans .env}", s["environment"])

    def test_config_cluster(self):
        attendu = {"vip_admin": "192.168.10.251", "vrid": 51, "interface_heartbeat": "eth0.10",
                   "services_surveilles": {
                       n: {"nom_conteneur": n, "chemin_compose": c, "priorite_pi31": 100, "priorite_pi32": 90,
                           "adresses": a}  # vérifiées par ARP avant démarrage (H6)
                       for n, c, a in (
                           ("api-rincage", "api/rincage", [{"ip": "192.168.20.20", "interface": "eth0.20"},
                                                           {"ip": "192.168.30.20", "interface": "eth0.30"}]),
                           ("sim-rincage", "simulation/rincage", [{"ip": "192.168.20.10", "interface": "eth0.20"}]))}}
        for n in ("pi31", "pi32"):
            self.assertEqual(json.loads(self.f[f"{n}/config_cluster.json"]), attendu)

    def test_macvlan(self):
        for n in ("pi31", "pi32", "pi51"):
            for arg in ("parent=eth0.20", "--subnet=192.168.20.0/24", "--gateway=192.168.20.1",
                        "--ip-range=192.168.20.16/28", "parent=eth0.30", "--ip-range=192.168.30.16/28"):
                self.assertIn(arg, self.f[f"{n}/creation_vlan.sh"])

    def test_services_deployes_sur_chaque_membre(self):
        self.assertIn("pi32/api/rincage/docker-compose.yml", self.f)
        self.assertIn("pi51/agent-sync/sync-vlan-30/docker-compose.yml", self.f)  # dossier réel (audit actif)
        self.assertNotIn("pi51/api/rincage/docker-compose.yml", self.f)

    def test_sortie_videe_seulement_si_marquee(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            sortie = Path(d) / "genere"
            generer(self.m, sortie)
            (sortie / "pi51" / "perime").mkdir()
            generer(self.m, sortie)
            self.assertFalse((sortie / "pi51" / "perime").exists())  # plus de fichier périmé
            autre = Path(d) / "autre"
            autre.mkdir()
            (autre / "precieux.txt").write_text("x")
            with self.assertRaises(SystemExit):
                generer(self.m, autre)
            self.assertTrue((autre / "precieux.txt").exists())

    def test_topologie(self):
        page = self.f["topologie.html"]
        donnees = json.loads(page.split("const D = ", 1)[1].split(";\n", 1)[0])
        ids = {n["id"] for n in donnees["noeuds"]}
        self.assertTrue({"pi31", "vlan20", "api-rincage", "cluster:fonctionnel", "vrrp:coeur-sii"} <= ids)
        self.assertTrue(all(l["from"] in ids and l["to"] in ids for l in donnees["liens"]))  # aucun lien orphelin
        rouges = [l for l in donnees["liens"] if l["couche"] == "flux" and l["color"] == "#dc2626"]
        self.assertEqual(len(rouges), 5)  # les 5 flux qui traversent le pare-feu

    def test_matrice_de_flux(self):
        lignes = {(l["client"], l["service"]): l for l in flux(self.m)}
        self.assertEqual(lignes[("api-rincage", "sim-rincage/modbus")]["pare_feu"], "non")
        rsync = lignes[("sync-vlan-20", "pi31/ssh")]
        self.assertEqual((rsync["source"], rsync["destination"], rsync["pare_feu"]),
                         ("192.168.20.31", "192.168.10.10", "oui"))  # audit D4
        self.assertEqual(lignes[("poste-admin", "api-rincage/opcua")]["destination"], "192.168.30.20")


def collecte_conforme(m, noeud):
    """Ce que collecte.sh renverrait sur un nœud parfaitement aligné sur le modèle."""
    eq = m["equipements"][noeud]
    adresses = [{"ifname": "lo", "addr_info": [{"family": "inet", "local": "127.0.0.1", "prefixlen": 8}]}]
    for inom, itf in eq["interfaces"].items():
        infos = []
        if itf.get("ip"):
            ip, masque = itf["ip"].split("/")
            infos.append({"family": "inet", "local": ip, "prefixlen": int(masque)})
        adresses.append({"ifname": inom, "addr_info": infos})
    reseaux = []
    for nom, r in reseaux_macvlan(m, noeud).items():
        reseaux.append({"Name": nom, "Options": {"parent": r["parent"]},
                        "IPAM": {"Config": [{"Subnet": r["subnet"], "Gateway": r["gateway"], "IPRange": r["ip_range"]}]}})
    inspect = []
    for s in m["services"].values():
        if s["cluster"] not in clusters_de(eq):
            continue
        inspect.append({
            "Name": "/" + s["compose"]["container_name"],
            "Config": {"Image": s["compose"]["image"], "Labels": {
                "com.docker.compose.project.working_dir": f"{eq['contexte']['racine_projets']}/{s['chemin']}"}},
            "State": {"Status": "running"},
            "NetworkSettings": {"Networks": {r: {"IPAMConfig": {"IPv4Address": a.split("/")[0]}}
                                             for r, a in (s.get("ip") or {}).items()}}})
    return {"hote": noeud, "adresses": adresses, "reseaux": reseaux, "inspect": inspect}


class TestDerive(unittest.TestCase):
    def setUp(self):
        self.m = charger()
        self.c = {n: collecte_conforme(self.m, n) for n in ("pi31", "pi32", "pi51")}

    def ecarts(self):
        return [t for niveau, t in deriver(self.m, self.c) if niveau == ECART]

    def test_conforme_sans_ecart(self):
        self.assertEqual(self.ecarts(), [])

    def test_conteneur_oublie(self):  # audit D11
        self.c["pi31"]["inspect"].append({"Name": "/test-opcua-srv", "Config": {"Image": "x"}, "State": {}})
        self.assertEqual(self.ecarts(), ["pi31 : conteneur test-opcua-srv présent mais absent du modèle"])

    def test_mauvaise_ip_et_mauvais_dossier(self):
        ct = self.c["pi51"]["inspect"][0]
        ct["NetworkSettings"]["Networks"]["vlan20"]["IPAMConfig"]["IPv4Address"] = "192.168.20.99"
        ct["Config"]["Labels"]["com.docker.compose.project.working_dir"] = "/home/pi51/donnees/serveur/donnees-vlan-20"
        e = self.ecarts()
        self.assertEqual(len(e), 2, e)
        self.assertIn("attendu 192.168.20.30/24", e[0])
        self.assertIn("déployé depuis /home/pi51/donnees/serveur/donnees-vlan-20", e[1])

    def test_vip_sur_le_maitre_n_est_pas_un_ecart(self):
        for a in self.c["pi31"]["adresses"]:
            if a["ifname"] == "eth0.10":
                a["addr_info"].append({"family": "inet", "local": "192.168.10.251", "prefixlen": 24})
        self.assertEqual(self.ecarts(), [])

    def test_reseau_macvlan_different(self):  # audit H9 si on change la plage
        self.c["pi32"]["reseaux"][0]["IPAM"]["Config"][0]["IPRange"] = "192.168.20.224/27"
        self.assertEqual(self.ecarts(), ["pi32 : réseau vlan20 : ip_range = 192.168.20.224/27, attendu 192.168.20.16/28"])


if __name__ == "__main__":
    unittest.main()
