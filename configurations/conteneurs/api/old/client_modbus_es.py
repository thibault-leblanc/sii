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