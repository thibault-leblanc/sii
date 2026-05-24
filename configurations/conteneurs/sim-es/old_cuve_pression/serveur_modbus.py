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