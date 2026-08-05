import asyncio
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSequentialDataBlock

class BlocDonneesSimulation(ModbusSequentialDataBlock):
    def __init__(self, memoire, config_mapping):
        self.memoire = memoire
        self.mapping = config_mapping
        # On alloue un bloc de 100 adresses pour avoir de la marge
        super().__init__(address=0, values=[0]*100)

    def getValues(self, address, count=1):
        valeurs = []
        for adr in range(address, address + count):
            val = 0
            adr_str = str(adr)
            
            # Actionneurs (Coils)
            if adr_str in self.mapping.get("coils", {}):
                val = 1 if self.memoire.get(self.mapping["coils"][adr_str]) else 0
                
            # Capteurs Tout ou Rien (Discrete Inputs)
            elif adr_str in self.mapping.get("discrete_inputs", {}):
                val = 1 if self.memoire.get(self.mapping["discrete_inputs"][adr_str]) else 0
                
            # Capteurs Analogiques (Input Registers) - Application du Scale Modbus
            elif adr_str in self.mapping.get("input_registers", {}):
                reg_config = self.mapping["input_registers"][adr_str]
                raw_val = self.memoire.get(reg_config["var"], 0.0)
                val = int(raw_val * reg_config["scale"])
                
            valeurs.append(val)
        return valeurs

    def setValues(self, address, values):
        # L'automate n'a le droit d'écrire que sur les Coils (Actionneurs)
        for i, val in enumerate(values):
            adr = str(address + i)
            if adr in self.mapping.get("coils", {}):
                var_name = self.mapping["coils"][adr]
                booleen = (val != 0)
                self.memoire.set(var_name, booleen)

async def lancer_serveur_modbus(memoire, config_network, config_mapping):
    hote = config_network.get("host", "0.0.0.0")
    port = config_network.get("port", 502)
    print(f"[MODBUS] Serveur en écoute sur {hote}:{port}...")
    
    bloc = BlocDonneesSimulation(memoire, config_mapping)
    contexte_esclave = ModbusSlaveContext(di=bloc, co=bloc, hr=bloc, ir=bloc, zero_mode=True)
    contexte = ModbusServerContext(slaves=contexte_esclave, single=True)
    
    await StartAsyncTcpServer(context=contexte, address=(hote, port))