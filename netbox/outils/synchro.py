"""Met toute l'IaC du repo à jour depuis NetBox, en une commande.

    python netbox/outils/synchro.py              # export NetBox -> sii.yaml -> iaac/infrastructure.json -> génération -> tests
    python netbox/outils/synchro.py --verifier   # n'écrit rien : code 1 si le repo n'est pas à jour (garde-fou de commit)

NetBox est joint par NETBOX_URL et NETBOX_TOKEN. Sans eux (ou sans pynetbox), l'étape NetBox est sautée avec un
avertissement : les contrôles hors ligne (modèle, IaC, tests) restent faits.
"""
import argparse
import os
import subprocess
import sys

from modele import RACINE_REPO, SOURCE_DEFAUT, charger, console_utf8, differences, ecrire_yaml, normaliser, valider

NETBOX = RACINE_REPO / "netbox"


def etape(titre):
    print(f"\n== {titre}")


def netbox(verifier):
    """Retourne True si OK (ou sauté), False si le repo diverge de NetBox."""
    if not (os.environ.get("NETBOX_URL") and os.environ.get("NETBOX_TOKEN")):
        print("  ! NETBOX_URL / NETBOX_TOKEN non définis : comparaison avec NetBox SAUTÉE")
        return True
    try:
        from exporter import ENTETE, exporter
        from importer import connecter
        nb = connecter()
        export = exporter(nb)
    except Exception as e:  # NetBox arrêté, jeton révoqué, pynetbox absent...
        print(f"  ! NetBox injoignable ({type(e).__name__}) : comparaison avec NetBox SAUTÉE")
        return True
    source = charger(SOURCE_DEFAUT)
    ecarts = differences(normaliser(source), normaliser(export))
    if verifier:
        for e in ecarts:
            print(f"  ✗ {e}")
        print(f"  NetBox / sii.yaml : {len(ecarts)} écart(s)")
        return not ecarts
    if source.get("a_verifier"):
        export = {"a_verifier": source["a_verifier"], **export}
    ecrire_yaml(export, SOURCE_DEFAUT, ENTETE)
    print(f"  sii.yaml réécrit depuis NetBox ({len(ecarts)} changement(s))")
    return True


def main():
    console_utf8()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--verifier", action="store_true", help="ne rien écrire ; code 1 si le repo n'est pas à jour")
    args = p.parse_args()
    ok = True

    etape("1. NetBox -> netbox/donnees/sii.yaml")
    ok &= netbox(args.verifier)

    etape("2. Validation du modèle")
    erreurs, _ = valider(charger(SOURCE_DEFAUT))
    for e in erreurs:
        print(f"  ✗ {e}")
    print(f"  {len(erreurs)} erreur(s)")
    ok &= not erreurs

    etape("3. iaac/infrastructure.json")
    r = subprocess.run([sys.executable, str(NETBOX / "outils" / "vers_iaac.py")] + (["--verifier"] if args.verifier else []))
    ok &= r.returncode == 0

    if not args.verifier:
        etape("4. Génération (netbox/genere/)")
        subprocess.run([sys.executable, str(NETBOX / "outils" / "generer.py"), "-o", str(NETBOX / "genere")],
                       stdout=subprocess.DEVNULL, check=True)
        print("  netbox/genere/ régénéré")

    etape("5. Tests")
    for dossier, cwd in (("tests", NETBOX), ("tests", RACINE_REPO)):
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", dossier], cwd=cwd,
                           capture_output=True, text=True)
        print(f"  {cwd.relative_to(RACINE_REPO.parent)}/{dossier} : {'OK' if r.returncode == 0 else 'ÉCHEC'}")
        if r.returncode:
            print(r.stderr[-2000:])
        ok &= r.returncode == 0

    if not args.verifier:
        etape("Changements à relire avant commit")
        subprocess.run(["git", "status", "--short", "--", "netbox/donnees", "iaac"], cwd=RACINE_REPO)
    print(f"\n{'À JOUR' if ok else 'PAS À JOUR'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
