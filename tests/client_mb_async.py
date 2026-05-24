import asyncio
import logging
import platform
import subprocess
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

# 1. Activation des logs de PyModbus au niveau DEBUG
# Cela permet d'afficher les requêtes et les réponses (les trames héxadécimales)
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG 
)
logger = logging.getLogger(__name__)

def test_ping(host):
    """Vérifie si l'équipement répond sur le réseau avant même de tenter le Modbus."""
    logger.info(f"Test de ping vers l'adresse {host}...")
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    commande = ['ping', param, '1', host]
    
    try:
        # Exécution silencieuse du ping
        reponse = subprocess.call(commande, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if reponse == 0:
            logger.info("✅ Ping réussi : L'équipement est joignable sur le réseau.")
            return True
        else:
            logger.error("❌ Échec du ping : L'équipement est injoignable (Éteint ? Mauvais sous-réseau ? Câble débranché ?).")
            return False
    except Exception as e:
        logger.error(f"Erreur lors du test de ping : {e}")
        return False

class AutomateModbusClient:
    def __init__(self, host, port):
        # On stocke les variables directement dans notre classe
        self.host = host
        self.port = port
        self.client = AsyncModbusTcpClient(host, port=port, timeout=3.0, retries=1)

    async def connecter(self):
        # On utilise nos propres variables ici
        logger.info(f"Tentative de connexion TCP Modbus sur {self.host}:{self.port}...")
        try:
            await self.client.connect()
            if self.client.connected:
                logger.info("✅ Connexion Modbus TCP (Port 502) établie avec succès !")
                return True
            else:
                logger.error("❌ La connexion a été refusée (Le port 502 est fermé ou le service n'est pas démarré sur la cible).")
                return False
        except asyncio.TimeoutError:
            logger.error("❌ Timeout : Le serveur n'a pas répondu à la demande de connexion.")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur inattendue lors de la connexion : {e}")
            return False

    def deconnecter(self):
        if self.client.connected:
            logger.info("Fermeture de la connexion.")
            self.client.close()

    async def lire_entrees(self):
        if not self.client.connected:
            logger.warning("Impossible de lire : le client n'est pas connecté.")
            return None

        try:
            logger.info("Demande de lecture des Input Registers 20 et 21 (Slave ID: 1)...")
            resultat = await self.client.read_input_registers(address=20, count=2, device_id=1)

            if resultat.isError():
                if isinstance(resultat, ExceptionResponse):
                    logger.error(f"❌ L'automate a renvoyé une exception Modbus (Code: {resultat.exception_code})")
                    if resultat.exception_code == 2:
                        logger.error(" -> Code 2 (Illegal Data Address) : L'adresse 20 n'existe pas dans la table de l'automate.")
                    elif resultat.exception_code == 3:
                        logger.error(" -> Code 3 (Illegal Data Value) : Problème de format de données.")
                else:
                    logger.error(f"❌ La trame est invalide ou vide : {resultat}")
                return None

            logger.info("✅ Réponse Modbus reçue et valide.")
            entrees = {
                "niveau_acide": resultat.registers[0] / 10.0,
                "qualite_acide": resultat.registers[1] / 100.0
            }
            return entrees

        except ModbusException as e:
            logger.error(f"❌ Erreur interne PyModbus : {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur Python générale : {e}")
            return None
        
async def main():
    HOST = '192.168.20.10'
    PORT = 502

    print("\n" + "="*40 + "\nDÉBUT DU DIAGNOSTIC\n" + "="*40)
    
    # 1. Test réseau basique
    if not test_ping(HOST):
        print("\n⚠️ ATTENTION : Le Ping ne passe pas.")
        print("Vérifiez que votre PC a bien une adresse IP dans le même sous-réseau (ex: 192.168.20.X).")
        print("Poursuite des tests tout de même...\n")
    
    # 2. Test de connexion
    automate = AutomateModbusClient(HOST, PORT)
    if await automate.connecter():
        
        # 3. Test de lecture
        donnees = await automate.lire_entrees()
        
        if donnees:
            print("\n📊 === RÉSULTATS === ")
            print(f" -> Niveau d'acide : {donnees['niveau_acide']} %")
            print(f" -> Qualité (pH)   : {donnees['qualite_acide']}")
        else:
            print("\n❌ La lecture a échoué. Vérifiez :")
            print(" 1. Que l'ID de l'esclave (slave=1) est le bon. (Parfois slave=255 ou 0).")
            print(" 2. Que les Input Registers 20 et 21 sont bien configurés dans votre simulateur.")
            print(" 3. S'il ne s'agit pas plutôt de Holding Registers (fonction read_holding_registers).")
            
        automate.deconnecter()
    else:
        print("\n❌ Impossible de continuer sans connexion TCP validée.")

    print("\n" + "="*40 + "\nFIN DU DIAGNOSTIC\n" + "="*40)

if __name__ == "__main__":
    asyncio.run(main())