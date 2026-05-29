import json
import asyncio
import signal
import logging
from memoire_partagee import MemoirePartagee
from moteur_physique import MoteurPhysique
from serveur_modbus import lancer_serveur_modbus

# --- CONFIGURATION DES LOGS DE LA SIMULATION ---
logging.basicConfig(
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO # Remplacer par logging.DEBUG pour voir les pièces transiter
)
logger = logging.getLogger("SimuMaster")
logging.getLogger("pymodbus").setLevel(logging.WARNING)

async def principal():
    logger.info("=== DÉMARRAGE DU SIMULATEUR PHYSIQUE ===")
    
    # 1. Chargement du contrat Modbus/Physique
    try:
        with open("config_simu.json", "r") as f:
            config = json.load(f)
        logger.info("Fichier config_simu.json chargé.")
    except Exception as e:
        logger.critical(f"Erreur lors du chargement de la configuration : {e}")
        return

    # 2. Initialisation de la Cuve à froid
    etat_de_base = {
        "cmd_conv_entree": False, "cmd_moteur_tambour": False,
        "cmd_conv_sortie": False, "cmd_pompe_acide": False,
        "cmd_vanne_vidange": False, "detec_piece_entree": False,
        "detec_piece_sortie": False, "alarme_debordement": False
    }
    etat_de_base.update(config["initial_state"])
    memoire = MemoirePartagee(etat_de_base)

    # 3. Lancement du Moteur Physique (Le monde réel)
    moteur = MoteurPhysique(memoire, config["physics_parameters"])
    moteur.demarrer()

    # 4. Lancement de la Carte Réseau (Le serveur Modbus)
    tache_modbus = asyncio.create_task(
        lancer_serveur_modbus(memoire, config["network"], config["modbus_mapping"])
    )

    # 5. Maintien en vie et gestion de l'arrêt
    evenement_arret = asyncio.Event()
    boucle = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        boucle.add_signal_handler(sig, lambda s=sig: (
            logger.info(f"Signal d'arrêt {s.name} reçu."), 
            evenement_arret.set()
        ))

    logger.info("✅ Simulateur opérationnel. Attente des ordres de l'API...")
    await evenement_arret.wait()
    
    logger.info("Arrêt de la simulation en cours...")
    moteur.arreter()
    tache_modbus.cancel()
    logger.info("Simulation terminée.")

if __name__ == "__main__":
    asyncio.run(principal())