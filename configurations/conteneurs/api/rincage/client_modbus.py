import logging
from pymodbus.client import AsyncModbusTcpClient

logger = logging.getLogger("ModbusClient")

class AutomateModbusClient:
    def __init__(self, host, port):
        self.client = AsyncModbusTcpClient(host, port=port, timeout=2.0, retries=1)

    async def connecter(self):
        try:
            await self.client.connect()
        except Exception as e:
            logger.error(f"Erreur lors de la tentative de connexion : {e}")
        return self.client.connected

    async def deconnecter(self):
        try:
            self.client.close()
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du socket : {e}")

    async def lire_entrees(self):
        if not self.client.connected:
            return {}

        try:
            rr_di = await self.client.read_discrete_inputs(10, count=3, device_id=1)
            rr_ir = await self.client.read_input_registers(20, count=2, device_id=1)

            entrees = {}
            if not rr_di.isError():
                entrees["detec_piece_entree"] = rr_di.bits[0]
                entrees["detec_piece_sortie"] = rr_di.bits[1]
                entrees["alarme_debordement"] = rr_di.bits[2]
            
            if not rr_ir.isError():
                entrees["niveau_acide"] = rr_ir.registers[0] / 10.0
                entrees["qualite_acide"] = rr_ir.registers[1] / 100.0

            return entrees
        except Exception as e:
            logger.error(f"Erreur de lecture: {e}")
            return {}

    async def ecrire_sorties(self, sorties):
        if not self.client.connected or not sorties:
            return

        bits = [
            sorties.get("cmd_conv_entree", False),
            sorties.get("cmd_moteur_tambour", False),
            sorties.get("cmd_conv_sortie", False),
            sorties.get("cmd_pompe_acide", False),
            sorties.get("cmd_vanne_vidange", False)
        ]
        
        try:
            await self.client.write_coils(0, bits, device_id=1)
        except Exception as e:
            logger.error(f"Erreur d'écriture: {e}")