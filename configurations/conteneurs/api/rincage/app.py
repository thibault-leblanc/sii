import json
import asyncio
import signal
import time
import logging
from client_modbus import AutomateModbusClient
from serveur_opcua import initialiser_opcua
from logique import executer_logique

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d - [%(levelname)s] - %(name)s - %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO # Changé en INFO pour ne pas polluer l'écran une fois que ça marche
)
logger = logging.getLogger("AutomatePLC")
logging.getLogger("pymodbus").setLevel(logging.WARNING)
logging.getLogger("asyncua").setLevel(logging.WARNING)

async def principal():
    logger.info("Démarrage du processus Automate...")
    
    with open("config_api.json", "r") as f:
        config = json.load(f)

    scan_cycle = config["plc_settings"]["scan_cycle_ms"] / 1000.0

    logger.info("Lancement du serveur OPC-UA...")
    serveur_opcua, noeuds_opcua = await initialiser_opcua(config)
    await serveur_opcua.start()
    logger.info("✅ Serveur OPC-UA démarré.")

    modbus_cfg = config["modbus_client"]
    client_modbus = AutomateModbusClient(modbus_cfg["target_host"], int(modbus_cfg["target_port"]))
    
    await client_modbus.connecter()
    
    memoire_interne = {}
    evenement_arret = asyncio.Event()

    boucle = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        boucle.add_signal_handler(sig, lambda s=sig: (
            logger.info(f"Signal d'arrêt {s.name} reçu."), 
            evenement_arret.set()
        ))

    logger.info(f"🚀 Automate en cours d'exécution. Temps de cycle visé : {config['plc_settings']['scan_cycle_ms']}ms")
    
    numero_cycle = 0

    while not evenement_arret.is_set():
        debut_cycle = time.time()
        numero_cycle += 1

        # Reconnexion silencieuse si perte de terrain
        if not client_modbus.client.connected:
            if numero_cycle % 10 == 0:
                logger.warning("Modbus déconnecté. Tentative de reconnexion...")
            await client_modbus.connecter()

        # --- ÉTAPE 1 : LECTURE ---
        entrees = {}
        # 1.1 Lecture du Terrain (Modbus)
        if client_modbus.client.connected:
            entrees = await client_modbus.lire_entrees()
            
        # 1.2 Lecture des Ordres Supervision (OPC-UA) - MÊME SI MODBUS EST COUPÉ
        entrees["en_marche"] = await noeuds_opcua["EnMarche"].read_value()
        entrees["mode_auto"] = await noeuds_opcua["ModeAuto"].read_value()
        entrees["acquittement"] = await noeuds_opcua["AcquittementDefaut"].read_value()
        entrees["manu_pompe"] = await noeuds_opcua["ManuPompe"].read_value()
        entrees["manu_vanne"] = await noeuds_opcua["ManuVanne"].read_value()
        entrees["manu_tambour"] = await noeuds_opcua["ManuTambour"].read_value()

        # --- ÉTAPE 2 : LOGIQUE ---
        sorties = executer_logique(entrees, memoire_interne)

        # --- ÉTAPE 3 : ÉCRITURE TERRAIN ---
        if client_modbus.client.connected and sorties:
            await client_modbus.ecrire_sorties(sorties)

        # --- ÉTAPE 4 : MISE À JOUR SUPERVISION (OPC-UA) ---
        temps_execution = time.time() - debut_cycle
        
        await asyncio.gather(
            # Variables de Diagnostic Système
            noeuds_opcua["ConnexionSimuOk"].write_value(client_modbus.client.connected),
            noeuds_opcua["TempsCycleReelMs"].write_value(temps_execution * 1000.0),
            noeuds_opcua["Defaut"].write_value(memoire_interne.get("defaut", False)),
            
            # Capteurs (0.0 si déconnecté)
            noeuds_opcua["NiveauAcide"].write_value(entrees.get("niveau_acide", 0.0)),
            noeuds_opcua["QualiteAcide"].write_value(entrees.get("qualite_acide", 0.0)),
            
            # Actionneurs
            noeuds_opcua["PompeActive"].write_value(sorties.get("cmd_pompe_acide", False)),
            noeuds_opcua["VanneActive"].write_value(sorties.get("cmd_vanne_vidange", False)),
            noeuds_opcua["TambourTourne"].write_value(sorties.get("cmd_moteur_tambour", False)),
            noeuds_opcua["ConvoyeurEntree"].write_value(sorties.get("cmd_conv_entree", False)),
            noeuds_opcua["ConvoyeurSortie"].write_value(sorties.get("cmd_conv_sortie", False))
        )

        # Cadencement strict du cycle
        temps_restant = max(0, scan_cycle - (time.time() - debut_cycle))
        await asyncio.sleep(temps_restant)

    logger.info("Arrêt propre en cours...")
    await client_modbus.deconnecter()
    await serveur_opcua.stop()
    logger.info("Programme terminé.")

if __name__ == "__main__":
    asyncio.run(principal())