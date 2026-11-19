"""Tests du procédé de rinçage : logique de l'automate et physique du simulateur, sans réseau.

    python -m unittest discover -s tests      (depuis la racine du repo)
"""
import json
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "configurations/conteneurs/api/rincage"))
sys.path.insert(0, str(RACINE / "configurations/conteneurs/sim/rincage"))

from logique import executer_logique  # noqa: E402
from memoire_partagee import MemoirePartagee  # noqa: E402
from moteur_physique import MoteurPhysique  # noqa: E402

ARRET = {"cmd_pompe_acide": False, "cmd_vanne_vidange": False, "cmd_moteur_tambour": False,
         "cmd_conv_entree": False, "cmd_conv_sortie": False}


def entrees(niveau=60.0, ph=7.0, alarme=False, **commandes):
    e = {"niveau_acide": niveau, "qualite_acide": ph, "alarme_debordement": alarme,
         "en_marche": True, "mode_auto": True, "acquittement": False}
    e.update(commandes)
    return e


class TestLogique(unittest.TestCase):
    def test_lecture_incomplete_coupe_tout(self):  # audit, constat n°2
        for manquant in ("niveau_acide", "qualite_acide", "alarme_debordement"):
            with self.subTest(capteur=manquant):
                e = entrees(niveau=10.0)  # cuve basse : la pompe démarrerait
                del e[manquant]
                self.assertEqual(executer_logique(e, {}), ARRET)

    def test_modbus_coupe_coupe_tout(self):
        self.assertEqual(executer_logique({"en_marche": True, "mode_auto": True}, {}), ARRET)
        self.assertEqual(executer_logique({"mode_auto": False, "manu_pompe": True}, {}), ARRET)

    def test_hysteresis_niveau(self):
        m = {}
        self.assertTrue(executer_logique(entrees(niveau=40.0), m)["cmd_pompe_acide"])
        self.assertTrue(executer_logique(entrees(niveau=60.0), m)["cmd_pompe_acide"])   # garde l'état
        self.assertFalse(executer_logique(entrees(niveau=80.0), m)["cmd_pompe_acide"])
        self.assertFalse(executer_logique(entrees(niveau=60.0), m)["cmd_pompe_acide"])  # garde l'état

    def test_vidange_chimique(self):
        m = {}
        s = executer_logique(entrees(niveau=70.0, ph=4.9), m)
        self.assertTrue(s["cmd_vanne_vidange"])
        self.assertFalse(s["cmd_conv_entree"] or s["cmd_pompe_acide"])
        s = executer_logique(entrees(niveau=30.0, ph=4.9), m)  # pas de remplissage pendant la purge
        self.assertFalse(s["cmd_pompe_acide"])
        executer_logique(entrees(niveau=5.0, ph=4.9), m)       # fin de purge
        self.assertFalse(m["mode_vidange"])
        s = executer_logique(entrees(niveau=5.0, ph=4.9), m)   # pH encore bas : pas de nouvelle purge
        self.assertEqual((s["cmd_vanne_vidange"], s["cmd_pompe_acide"], s["cmd_conv_entree"]), (False, True, False))
        s = executer_logique(entrees(niveau=80.0, ph=6.8), m)  # cuve pleine d'acide neuf
        self.assertFalse(s["cmd_pompe_acide"])
        s = executer_logique(entrees(niveau=80.0, ph=6.8), m)  # la production reprend
        self.assertTrue(s["cmd_conv_entree"])

    def test_defaut_debordement_et_acquittement(self):
        m = {}
        self.assertEqual(executer_logique(entrees(alarme=True), m), ARRET)
        self.assertTrue(m["defaut"])
        executer_logique(entrees(alarme=True, acquittement=True), m)
        self.assertTrue(m["defaut"])  # pas d'acquittement tant que l'alarme est là
        executer_logique(entrees(acquittement=True), m)
        self.assertFalse(m["defaut"])

    def test_manuel_verrou_pompe_sur_alarme(self):
        s = executer_logique(entrees(alarme=True, mode_auto=False, manu_pompe=True, manu_vanne=True), {})
        self.assertFalse(s["cmd_pompe_acide"])
        self.assertTrue(s["cmd_vanne_vidange"])


class TestSimulateur(unittest.TestCase):
    def setUp(self):
        config = json.loads((RACINE / "configurations/conteneurs/sim/rincage/config_simu.json").read_text(encoding="utf-8"))
        etat = {**ARRET, "detec_piece_entree": False, "detec_piece_sortie": False, "alarme_debordement": False,
                **config["initial_state"]}
        self.memoire = MemoirePartagee(etat)
        self.sim = MoteurPhysique(self.memoire, config["physics_parameters"])

    def test_niveau_initial_respecte(self):  # audit P7
        self.sim.pas(1.0)
        self.assertAlmostEqual(self.memoire.get("niveau_acide"), 50.0)

    def test_acide_neuf_remonte_le_ph(self):  # audit P1
        self.memoire.set("qualite_acide", 4.0)
        self.memoire.set("cmd_pompe_acide", True)
        self.sim.pas(1.0)  # 500 l à pH 4 + 25 l à pH 7
        self.assertAlmostEqual(self.memoire.get("qualite_acide"), (500 * 4.0 + 25 * 7.0) / 525)

    def test_procede_complet_sans_vidange_infinie(self):
        """Simulateur et automate couplés, à la seconde, échelles Modbus comprises."""
        m, journal = {}, []
        for _ in range(4 * 3600):
            self.sim.pas(1.0)
            e = entrees(niveau=int(self.memoire.get("niveau_acide") * 10) / 10,
                        ph=int(self.memoire.get("qualite_acide") * 100) / 100,
                        alarme=self.memoire.get("alarme_debordement"))
            for cle, val in executer_logique(e, m).items():
                self.memoire.set(cle, val)
            journal.append((m.get("mode_vidange", False), e["qualite_acide"], e["alarme_debordement"]))

        vidanges = sum(1 for i in range(1, len(journal)) if journal[i][0] and not journal[i - 1][0])
        self.assertGreaterEqual(vidanges, 2, "le pH n'est jamais descendu sous 5 : test non probant")
        self.assertFalse(journal[-1][0] and journal[-600][0], "bloqué en vidange depuis 10 minutes")
        self.assertFalse(any(alarme for *_, alarme in journal), "débordement pendant le fonctionnement normal")
        self.assertGreater(max(ph for _, ph, _ in journal[len(journal) // 2:]), 6.0, "le pH ne se régénère pas")


if __name__ == "__main__":
    unittest.main()
