import asyncio
import random
from asyncua import Server


async def main():
    # 1. Initialiser le serveur
    server = Server()
    await server.init()

    # 2. Configurer le point de terminaison (Endpoint)
    # "0.0.0.0" permet d'accepter les connexions de n'importe quelle machine du réseau
    server.set_endpoint("opc.tcp://0.0.0.0:4848/freeopcua/server/")
    server.set_server_name("Mon Serveur OPC-UA Python")

    # 3. Créer un espace de noms (Namespace)
    uri = "http://exemples.fr/opcua"
    idx = await server.register_namespace(uri)

    # 4. Récupérer le nœud "Objects" racine
    node_objects = server.get_objects_node()

    # 5. Ajouter un Objet (un dossier/composant) dans l'arbre
    mon_capteur = await node_objects.add_object(idx, "Capteur_Interne")

    # 6. Ajouter une Variable à cet objet
    # On lui donne une valeur initiale (0.0) et on la rend modifiable par les clients (writable)
    var_temperature = await mon_capteur.add_variable(idx, "Temperature", 0.0)
    await var_temperature.set_writable()

    print(f"Serveur OPC-UA démarrer sur opc.tcp://localhost:4848/freeopcua/server/")
    print("Appuyez sur Ctrl+C pour l'arrêter.")

    # 7. Démarrer la boucle du serveur et mettre à jour la variable
    async with server:
        while True:
            # Simuler une variation de température
            nouvelle_temp = round(random.uniform(20.0, 25.0), 2)

            # Mettre à jour la valeur sur le serveur
            await var_temperature.write_value(nouvelle_temp)
            print(f"Mise à jour -> Température : {nouvelle_temp} °C")

            # Attendre 1 seconde avant la prochaine mesure
            await asyncio.sleep(1)


if __name__ == "__main__":
    # Lancer le programme asynchrone
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServeur arrêté proprement.")