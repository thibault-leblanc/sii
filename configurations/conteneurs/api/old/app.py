import asyncio
import signal
import os
from core_api import MoteurAutomate
from client_modbus_es import ClientTerrainModbus

async def boucle_automate(moteur, client_terrain):
    while True:
        await client_terrain.synchroniser(moteur.memoire)
        moteur.cycle_automate()
        await asyncio.sleep(0.1) # Protection CPU critique

async def principal():
    moteur = MoteurAutomate()
    client_terrain = ClientTerrainModbus()
    tache_automate = asyncio.create_task(boucle_automate(moteur, client_terrain))

    evenement_arret = asyncio.Event()
    boucle = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        boucle.add_signal_handler(sig, evenement_arret.set)

    print("[SYSTEME] Automate API prêt.")
    await evenement_arret.wait()
    tache_automate.cancel()

if __name__ == "__main__":
    asyncio.run(principal())