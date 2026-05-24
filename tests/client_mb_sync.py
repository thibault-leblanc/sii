from pymodbus.client import ModbusTcpClient

# Configuration de la cible (Ta simulation)
HOST = '192.168.20.10'
PORT = 502

print(f"Tentative de connexion à {HOST}:{PORT}...")
client = ModbusTcpClient(HOST, port=PORT)

if client.connect():
    print("✅ Connexion Modbus TCP réussie !")
    
    # On tente de lire les adresses 20 et 21 (Input Registers de ta table)
    # slave=1 est l'ID par défaut
    resultat = client.read_input_registers(address=20, count=2, slave=1)
    
    if not resultat.isError():
        niveau = resultat.registers[0] / 10.0
        qualite = resultat.registers[1] / 100.0
        print(f"📊 Lecture réussie :")
        print(f"   -> Niveau d'acide : {niveau} %")
        print(f"   -> Qualité (pH)   : {qualite}")
    else:
        print("❌ La connexion a réussi, mais la lecture des registres a échoué.")
        
    client.close()
else:
    print("❌ Impossible de se connecter. Le port 502 est fermé ou le serveur est éteint.")