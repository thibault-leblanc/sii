import asyncio
import signal
from opcua_server import initialiser_serveur

async def animer_donnees(noeuds, evenement_arret):
    """ Animation basique pour vérifier que le serveur est vivant """
    temp = 25.0
    while not evenement_arret.is_set():
        if "Temperature" in noeuds:
            temp += 0.5
            if temp > 80.0: temp = 25.0
            await noeuds["Temperature"].write_value(temp)
        
        # Pause obligatoire pour ne pas saturer le CPU
        await asyncio.sleep(1.0)

async def principal():
    print("[SYSTEME] Initialisation du serveur OPC-UA...")
    serveur, noeuds, url_serveur = await initialiser_serveur()
    
    await serveur.start()
    print(f"[SYSTEME] Serveur démarré avec succès !")
    print(f"[SYSTEME] Écoute active sur : {url_serveur}")

    # Gestion propre de l'arrêt du conteneur (SIGINT/SIGTERM)
    evenement_arret = asyncio.Event()
    boucle = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        boucle.add_signal_handler(sig, evenement_arret.set)

    # Lancement de la tâche d'animation en fond
    tache_anim = asyncio.create_task(animer_donnees(noeuds, evenement_arret))
    
    # Maintien en vie jusqu'à l'ordre d'arrêt
    await evenement_arret.wait()
    
    print("[SYSTEME] Ordre d'arrêt reçu. Fermeture du serveur...")
    tache_anim.cancel()
    await serveur.stop()

if __name__ == "__main__":
    asyncio.run(principal())