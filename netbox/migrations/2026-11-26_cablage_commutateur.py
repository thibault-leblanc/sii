"""Migration NetBox du 2026-11-26 : câblage du commutateur confirmé par l'administrateur. Relançable sans effet de bord.

    NETBOX_URL=... NETBOX_TOKEN=... python netbox/migrations/2026-11-26_cablage_commutateur.py

Contenu (voir documentation/audit_fonctionnel.md §10.3, constats S1 et S3) :
- port5 du commutateur : trunk VLAN 10, 20, 30 vers pi51, câblé à pi51/eth0 (pi51 n'avait pas de câble) ;
- port2 retiré : déclaré en accès VLAN10 pour le poste d'administration, rien n'y est branché (le poste est côté WAN).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outils"))
from importer import Importeur, connecter  # noqa: E402
from modele import INTERFACE_PHYSIQUE, console_utf8  # noqa: E402


def main():
    console_utf8()
    nb = connecter()
    imp = Importeur(nb, {})
    sw = nb.dcim.devices.get(name="commutateur")
    groupe = nb.ipam.vlan_groups.get(slug="sii").id
    vlans = [nb.ipam.vlans.get(vid=v, group_id=groupe).id for v in (10, 20, 30)]

    print("Port 5 : trunk vers pi51")
    port5 = imp.assurer(nb.dcim.interfaces, {"device_id": sw.id, "name": "port5"}, {
        "device": sw.id, "name": "port5", "type": INTERFACE_PHYSIQUE, "description": "trunk pi51",
        "mode": "tagged", "untagged_vlan": None, "tagged_vlans": vlans})
    eth0 = nb.dcim.interfaces.get(device_id=nb.dcim.devices.get(name="pi51").id, name="eth0")
    imp.cabler(eth0, port5)

    print("Port 2 : retiré (rien de branché)")
    port2 = nb.dcim.interfaces.get(device_id=sw.id, name="port2")
    if port2:
        port2.delete()
        print("  - commutateur/port2")

    print(f"Terminé : {imp.crees} création(s), {imp.modifies} modification(s) suivies.")


if __name__ == "__main__":
    main()
