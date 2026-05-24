import asyncio
import signal
from core_simulation import SimulateurEntreesSorties
from serveur_modbus import lancer_serveur_modbus

async def principal():
    simulateur = SimulateurEntreesSorties()
    tache_transport = asyncio.create_task(lancer_serveur_modbus(simulateur))

    evenement_arret = asyncio.Event()
    boucle = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        boucle.add_signal_handler(sig, evenement_arret.set)

    print("[SYSTEME] Simulateur ES opérationnel.")
    await evenement_arret.wait()
    
    simulateur.arreter()
    tache_transport.cancel()

if __name__ == "__main__":
    asyncio.run(principal())