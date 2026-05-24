mkdir -p ~/opcua-srv

# 1. Le Dockerfile (Toujours avec la protection RAM --no-compile)
cat << 'EOF' > ~/opcua-srv/Dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir --no-compile cryptography
RUN pip install --no-cache-dir --no-compile asyncua==1.1.5
COPY . .
EXPOSE 4840
CMD ["python", "-u", "app.py"]
EOF

# 2. Le docker-compose (Avec les deux pattes réseau)
cat << 'EOF' > ~/opcua-srv/docker-compose.yml
version: '3.8'
services:
  test_opcua:
    build: .
    container_name: test-opcua-srv
    restart: unless-stopped
    networks:
      vlan20:
        ipv4_address: 192.168.20.30
      vlan30:
        ipv4_address: 192.168.30.30

networks:
  vlan20:
    external: true
  vlan30:
    external: true
EOF

# 3. Le dictionnaire de variables (Modèle très simple)
cat << 'EOF' > ~/opcua-srv/config_opcua.json
{
  "namespace": "http://test.lab/opcua",
  "name": "Serveur_Test",
  "objects": {
    "MachineTest": {
      "Temperature": {"type": "Double", "writable": true, "initial": 25.0},
      "EnMarche": {"type": "Boolean", "writable": true, "initial": false}
    }
  }
}
EOF

# 4. Le module OPC-UA (Génère l'arborescence à partir du JSON)
cat << 'EOF' > ~/opcua-srv/opcua_server.py
import json
from asyncua import Server, ua

async def initialiser_serveur(chemin_config="config_opcua.json", port=4840):
    serveur = Server()
    await serveur.init()
    # 0.0.0.0 permet d'écouter sur les deux pattes réseau (.20.30 et .30.30)
    serveur.set_endpoint(f"opc.tcp://0.0.0.0:{port}/freeopcua/server/")

    with open(chemin_config, 'r') as f:
        config = json.load(f)

    idx = await serveur.register_namespace(config["namespace"])
    objet_racine = await serveur.nodes.objects.add_object(idx, config["name"])
    
    noeuds_crees = {}
    for nom_obj, variables in config["objects"].items():
        dossier = await objet_racine.add_object(idx, nom_obj)
        for nom_var, props in variables.items():
            val = props["initial"]
            # Typage asynchrone basique
            if props["type"] == "Double":
                var = await dossier.add_variable(idx, nom_var, float(val), varianttype=ua.VariantType.Double)
            else:
                var = await dossier.add_variable(idx, nom_var, bool(val), varianttype=ua.VariantType.Boolean)
            
            if props["writable"]:
                await var.set_writable()
            noeuds_crees[nom_var] = var
            
    return serveur, noeuds_crees
EOF

# 5. L'orchestrateur (Sécurisé pour le CPU)
cat << 'EOF' > ~/opcua-srv/app.py
import asyncio
import signal
from opcua_server import initialiser_serveur

async def animer_donnees(noeuds, evenement_arret):
    """ Petite tâche de fond pour faire vivre la variable sans charger le CPU """
    temp = 25.0
    while not evenement_arret.is_set():
        temp += 0.5
        if temp > 80.0: temp = 25.0
        await noeuds["Temperature"].write_value(temp)
        # PAUSE D'1 SECONDE : Protection absolue du processeur
        await asyncio.sleep(1.0) 

async def principal():
    print("[SYSTEME] Démarrage du serveur OPC-UA de test...")
    serveur, noeuds = await initialiser_serveur()
    await serveur.start()
    print("[SYSTEME] Serveur OPC-UA en écoute sur 0.0.0.0:4840")

    evenement_arret = asyncio.Event()
    boucle = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        boucle.add_signal_handler(sig, evenement_arret.set)

    # Lancement de l'animation des variables
    tache_anim = asyncio.create_task(animer_donnees(noeuds, evenement_arret))

    await evenement_arret.wait()
    
    print("[SYSTEME] Arrêt propre du conteneur...")
    tache_anim.cancel()
    await serveur.stop()

if __name__ == "__main__":
    asyncio.run(principal())
EOF