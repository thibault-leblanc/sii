#!/bin/bash

echo "====================================================="
echo "🚀 DÉPLOIEMENT DE L'INFRASTRUCTURE INDUSTRIELLE (OT) "
echo "====================================================="

# ---------------------------------------------------------
# 1. CONFIGURATION RÉSEAU (HÔTE)
# ---------------------------------------------------------
echo -e "\n[1/4] Configuration des VLANs sur l'hôte (Netplan)..."

sudo tee /etc/netplan/99-vlans-ot.yaml > /dev/null << 'EOF'
network:
  version: 2
  vlans:
    eth0.20:
      id: 20
      link: eth0
    eth0.30:
      id: 30
      link: eth0
EOF

sudo netplan apply
echo "✅ Interfaces eth0.20 et eth0.30 activées."

# ---------------------------------------------------------
# 2. RÉSEAUX DOCKER MACVLAN
# ---------------------------------------------------------
echo -e "\n[2/4] Création des réseaux Docker Macvlan..."

if ! sudo docker network ls | grep -q "vlan20"; then
    sudo docker network create -d macvlan \
      -o parent=eth0.20 \
      --subnet=192.168.20.0/24 \
      --gateway=192.168.20.1 \
      --ip-range=192.168.20.16/28 \
      vlan20
    echo "✅ Réseau vlan20 créé."
else
    echo "⚡ Réseau vlan20 déjà existant."
fi

if ! sudo docker network ls | grep -q "vlan30"; then
    sudo docker network create -d macvlan \
      -o parent=eth0.30 \
      --subnet=192.168.30.0/24 \
      --gateway=192.168.30.1 \
      --ip-range=192.168.30.16/28 \
      vlan30
    echo "✅ Réseau vlan30 créé."
else
    echo "⚡ Réseau vlan30 déjà existant."
fi

# ---------------------------------------------------------
# 3. BLOC TERRAIN (SIMULATEUR E/S)
# ---------------------------------------------------------
echo -e "\n[3/4] Génération des fichiers du Simulateur E/S..."
mkdir -p ~/simulateur-es

cat << 'EOF' > ~/simulateur-es/requirements.txt
pymodbus==3.4.0
EOF

cat << 'EOF' > ~/simulateur-es/Dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 502
CMD ["python", "-u", "app.py"]
EOF

cat << 'EOF' > ~/simulateur-es/docker-compose.yml
version: '3.8'
services:
  simulateur:
    build: .
    container_name: sim-entrees-sorties
    restart: unless-stopped
    networks:
      vlan20:
        ipv4_address: 192.168.20.10
networks:
  vlan20:
    external: true
EOF

cat << 'EOF' > ~/simulateur-es/core_simulation.py
import time
import threading

class SimulateurEntreesSorties:
    def __init__(self):
        self.variables = {
            "niveau": 0.0,
            "temperature": 20.0,
            "vanne_remplissage": False,
            "chauffage": False,
            "pompe_vidange": False
        }
        self.en_fonctionnement = True
        self.thread = threading.Thread(target=self._boucle_physique, daemon=True)
        self.thread.start()

    def _boucle_physique(self):
        while self.en_fonctionnement:
            if self.variables["vanne_remplissage"] and self.variables["niveau"] < 100.0:
                self.variables["niveau"] += 2.5
            if self.variables["pompe_vidange"] and self.variables["niveau"] > 0.0:
                self.variables["niveau"] -= 3.0
                
            if self.variables["chauffage"] and self.variables["niveau"] > 10.0:
                self.variables["temperature"] += 1.2
            else:
                if self.variables["temperature"] > 20.0:
                    self.variables["temperature"] -= 0.3

            self.variables["niveau"] = max(0.0, min(100.0, self.variables["niveau"]))
            self.variables["temperature"] = max(20.0, min(100.0, self.variables["temperature"]))
            time.sleep(1.0) 

    def arreter(self):
        self.en_fonctionnement = False
        self.thread.join()
EOF

cat << 'EOF' > ~/simulateur-es/serveur_modbus.py
import asyncio
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock

class BlocDonneesSimulation(ModbusSequentialDataBlock):
    def __init__(self, simulateur):
        self.simulateur = simulateur
        super().__init__(address=0, values=[0]*10)

    def getValues(self, adresse, quantite=1):
        valeurs = []
        for adr in range(adresse, adresse + quantite):
            if adr == 0:   valeurs.append(int(self.simulateur.variables["niveau"] * 10))
            elif adr == 1: valeurs.append(int(self.simulateur.variables["temperature"] * 10))
            elif adr == 2: valeurs.append(1 if self.simulateur.variables["vanne_remplissage"] else 0)
            elif adr == 3: valeurs.append(1 if self.simulateur.variables["chauffage"] else 0)
            elif adr == 4: valeurs.append(1 if self.simulateur.variables["pompe_vidange"] else 0)
            else:          valeurs.append(0)
        return valeurs

    def setValues(self, adresse, valeurs):
        for i, val in enumerate(valeurs):
            adresse_courante = adresse + i
            if adresse_courante == 2:
                self.simulateur.variables["vanne_remplissage"] = (val == 1)
            elif adresse_courante == 3:
                self.simulateur.variables["chauffage"] = (val == 1)
            elif adresse_courante == 4:
                self.simulateur.variables["pompe_vidange"] = (val == 1)

async def lancer_serveur_modbus(simulateur, hote="0.0.0.0", port=502):
    print(f"[MODBUS SIMULATEUR] Écoute sur {hote}:{port}...")
    bloc = BlocDonneesSimulation(simulateur)
    memoire = ModbusSlaveContext(di=bloc, co=bloc, hr=bloc, ir=bloc, zero_mode=True)
    contexte = ModbusServerContext(slaves=memoire, single=True)
    await StartAsyncTcpServer(context=contexte, address=(hote, port))
EOF

cat << 'EOF' > ~/simulateur-es/app.py
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
EOF
echo "✅ Fichiers du simulateur générés."

# ---------------------------------------------------------
# 4. BLOC CONTRÔLE (API M580 VIRTUEL)
# ---------------------------------------------------------
echo -e "\n[4/4] Génération des fichiers de l'Automate (API)..."
mkdir -p ~/api

cat << 'EOF' > ~/api/Dockerfile
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir pymodbus==3.4.0
RUN pip install --no-cache-dir --no-compile cryptography
RUN pip install --no-cache-dir --no-compile asyncua==1.1.5

COPY . .
EXPOSE 502 4840
CMD ["python", "-u", "app.py"]
EOF

cat << 'EOF' > ~/api/docker-compose.yml
version: '3.8'
services:
  automate_api:
    build: .
    container_name: opcua-core-api
    restart: unless-stopped
    environment:
      - SCADA_PROTOCOL=OPCUA
      - IO_SIMULATOR_IP=192.168.20.10
    networks:
      vlan20:
        ipv4_address: 192.168.20.20
      vlan30:
        ipv4_address: 192.168.30.20

networks:
  vlan20:
    external: true
  vlan30:
    external: true
EOF

cat << 'EOF' > ~/api/config_opcua_srv.json
{
  "namespace": "http://usine.lab/api",
  "name": "api1",
  "objects": {
    "ProcessCuve": {
      "Niveau": {"type": "Double", "writable": false, "initial": 0.0},
      "Temperature": {"type": "Double", "writable": false, "initial": 20.0},
      "VanneRemplissage": {"type": "Boolean", "writable": true, "initial": false},
      "Chauffage": {"type": "Boolean", "writable": true, "initial": false},
      "PompeVidange": {"type": "Boolean", "writable": true, "initial": false},
      "ConsigneTemp": {"type": "Double", "writable": true, "initial": 45.0},
      "ModeAuto": {"type": "Boolean", "writable": true, "initial": false},
      "Marche": {"type": "Boolean", "writable": true, "initial": false}
    }
  }
}
EOF

cat << 'EOF' > ~/api/core_api.py
class MoteurAutomate:
    def __init__(self):
        self.memoire = {
            "Niveau": 0.0,
            "Temperature": 20.0,
            "VanneRemplissage": False,
            "Chauffage": False,
            "PompeVidange": False,
            "ConsigneTemp": 45.0,
            "ModeAuto": False,
            "Marche": False,
            "Etape_Grafcet": 0
        }
    
    def cycle_automate(self):
        m = self.memoire
        
        # Sécurité Matérielle absolue
        if m["Chauffage"] and m["Niveau"] < 10.0:
            m["Chauffage"] = False

        # Si Mode Manuel, l'automate ne fait rien de plus
        if not m["ModeAuto"]:
            return

        # Cycle Automatique
        if not m["Marche"]:
            m["VanneRemplissage"] = False
            m["Chauffage"] = False
            m["PompeVidange"] = False
            m["Etape_Grafcet"] = 0
            return

        if m["Etape_Grafcet"] == 0: 
            if m["Niveau"] < 5.0: m["Etape_Grafcet"] = 1
            else: m["Etape_Grafcet"] = 3 
                
        elif m["Etape_Grafcet"] == 1:
            m["VanneRemplissage"] = True
            if m["Niveau"] >= 80.0:
                m["VanneRemplissage"] = False
                m["Etape_Grafcet"] = 2
                
        elif m["Etape_Grafcet"] == 2:
            m["Chauffage"] = True
            if m["Temperature"] >= m["ConsigneTemp"]:
                m["Chauffage"] = False
                m["Etape_Grafcet"] = 3
                
        elif m["Etape_Grafcet"] == 3:
            m["PompeVidange"] = True
            if m["Niveau"] <= 1.0:
                m["PompeVidange"] = False
                m["Etape_Grafcet"] = 1
EOF

cat << 'EOF' > ~/api/client_modbus_es.py
from pymodbus.client import AsyncModbusTcpClient
import os

class ClientTerrainModbus:
    def __init__(self):
        self.ip_cible = os.environ.get("IO_SIMULATOR_IP", "192.168.20.10")
        self.client = AsyncModbusTcpClient(self.ip_cible, port=502)
        self.connecte = False

    async def synchroniser(self, memoire_automate):
        if not self.connecte:
            self.connecte = await self.client.connect()
            if not self.connecte:
                return

        try:
            # Lecture Niveau & Température
            lecture = await self.client.read_holding_registers(address=0, count=2, slave=1)
            if not lecture.isError():
                memoire_automate["Niveau"] = lecture.registers[0] / 10.0
                memoire_automate["Temperature"] = lecture.registers[1] / 10.0

            # Écriture Actionneurs
            sorties = [
                1 if memoire_automate["VanneRemplissage"] else 0,
                1 if memoire_automate["Chauffage"] else 0,
                1 if memoire_automate["PompeVidange"] else 0
            ]
            await self.client.write_registers(address=2, values=sorties, slave=1)
            
        except Exception:
            self.connecte = False
EOF

cat << 'EOF' > ~/api/app.py
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
EOF
echo "✅ Fichiers de l'Automate API générés."

echo -e "\n====================================================="
echo "🎉 DÉPLOIEMENT TERMINÉ ! TOUT EST PRÊT."
echo "====================================================="
echo "Pour compiler et lancer les deux plateformes :"
echo "1. cd ~/simulateur-es && sudo docker compose up --build -d"
echo "2. cd ~/api && sudo docker compose up --build -d"
echo "====================================================="