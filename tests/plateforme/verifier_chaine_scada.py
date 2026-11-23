"""Vérification de bout en bout de la chaîne de conduite, sur la plateforme allumée.

    FUXA (API web) -> OPC-UA -> automate -> Modbus TCP -> simulateur

Depuis le poste d'administration (routes vers les VLAN par le pare-feu, pymodbus installé) :

    python tests/plateforme/verifier_chaine_scada.py            # lecture seule
    python tests/plateforme/verifier_chaine_scada.py --marche   # envoie aussi « Marche » et vérifie l'effet

Lecture : FUXA remonte l'état de l'automate (connexion au simulateur, niveau, pH).
Avec --marche : FUXA écrit EnMarche = vrai ; l'effet est contrôlé de façon INDÉPENDANTE de FUXA et de l'automate,
en lisant directement les bobines du simulateur en Modbus. Le procédé reste ensuite en marche.
Ce n'est pas un test unitaire (il demande la plateforme) : il n'est pas lancé par « unittest discover ».
"""
import argparse
import asyncio
import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

FUXA = "http://192.168.30.10:1881"
SIMULATEUR = ("192.168.20.10", 502)
PROJET = Path(__file__).resolve().parents[2] / "configurations/conteneurs/scada/donnees/project.fuxap.db"
BOBINES = ["conv_entree", "tambour", "conv_sortie", "pompe", "vanne"]


def variables_opcua():
    """Identifiants FUXA des variables de l'équipement OPCUA_RINCAGE, lus dans le projet versionné."""
    base = sqlite3.connect(f"file:{PROJET}?mode=ro", uri=True)
    for (valeur,) in base.execute("select value from devices"):
        equipement = json.loads(valeur)
        if equipement.get("name") == "OPCUA_RINCAGE":
            return {t["name"]: tid for tid, t in equipement["tags"].items()}
    sys.exit("Équipement OPCUA_RINCAGE absent du projet FUXA")


def lire(ids):
    requete = urllib.parse.urlencode({"ids": json.dumps(list(ids.values()))})
    with urllib.request.urlopen(f"{FUXA}/api/getTagValue?{requete}", timeout=10) as r:
        noms = {v: k for k, v in ids.items()}
        return {noms[v["id"]]: v.get("value") for v in json.load(r)}


def ecrire(tag_id, valeur):
    corps = json.dumps({"tags": [{"id": tag_id, "value": valeur}]}).encode()
    req = urllib.request.Request(f"{FUXA}/api/setTagValue", data=corps, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


async def bobines_simulateur():
    from pymodbus.client import AsyncModbusTcpClient
    client = AsyncModbusTcpClient(SIMULATEUR[0], port=SIMULATEUR[1], timeout=3)
    await client.connect()
    reponse = await client.read_coils(0, count=len(BOBINES), device_id=1)
    client.close()
    return dict(zip(BOBINES, reponse.bits[:len(BOBINES)]))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--marche", action="store_true", help="envoyer « Marche » par FUXA et vérifier l'effet")
    args = p.parse_args()
    ids = variables_opcua()

    v = lire(ids)
    print("1. Remontée (lue dans FUXA) :", {k: v[k] for k in ("ConnexionSimuOk", "EnMarche", "ModeAuto", "Defaut",
                                                            "NiveauAcide", "QualiteAcide", "TempsCycleReelMs")})
    assert v["ConnexionSimuOk"] is True, "ÉCHEC : l'automate ne voit pas le simulateur (ou FUXA ne voit pas l'automate)"
    if args.marche:
        print("2. Descente : FUXA écrit EnMarche = vrai -> HTTP", ecrire(ids["EnMarche"], True))
        time.sleep(4)
        b = asyncio.run(bobines_simulateur())
        print("3. Contrôle indépendant (bobines du simulateur, Modbus direct) :", b)
        assert b["tambour"] and b["conv_entree"], "ÉCHEC : la commande n'est pas arrivée au simulateur"
    a = lire(ids)
    time.sleep(30)
    z = lire(ids)
    print(f"4. Dynamique sur 30 s : pH {a['QualiteAcide']} -> {z['QualiteAcide']}, "
          f"niveau {a['NiveauAcide']} -> {z['NiveauAcide']} %")
    print("RÉSULTAT : chaîne de conduite VALIDÉE")


if __name__ == "__main__":
    main()
