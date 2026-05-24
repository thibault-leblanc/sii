import json
from asyncua import Server, ua

async def initialiser_serveur(chemin_config="config_opcua.json"):
    # 1. Lecture du fichier de configuration
    with open(chemin_config, 'r') as f:
        config = json.load(f)

    serveur = Server()
    await serveur.init()

    # 2. Configuration réseau et identité
    conf_serveur = config.get("server", {})
    ip = conf_serveur.get("ip", "0.0.0.0")
    port = conf_serveur.get("port", 4840)
    path = conf_serveur.get("endpoint_path", "/freeopcua/server/")
    nom_serveur = conf_serveur.get("name", "Serveur_Generique")
    namespace_uri = conf_serveur.get("namespace", "http://default.local")
    
    url = f"opc.tcp://{ip}:{port}{path}"
    serveur.set_endpoint(url)
    serveur.set_server_name(nom_serveur)

    # 3. Sécurité
    if conf_serveur.get("security") == "None":
        serveur.set_security_policy([ua.SecurityPolicyType.NoSecurity])

    # 4. Création de l'arborescence et des variables (Data Model)
    idx = await serveur.register_namespace(namespace_uri)
    objet_racine = await serveur.nodes.objects.add_object(idx, nom_serveur)
    
    noeuds_crees = {}
    for nom_obj, variables in config.get("objects", {}).items():
        dossier = await objet_racine.add_object(idx, nom_obj)
        for nom_var, props in variables.items():
            val = props["initial"]
            # Typage dynamique
            if props["type"] == "Double":
                var = await dossier.add_variable(idx, nom_var, float(val), varianttype=ua.VariantType.Double)
            else:
                var = await dossier.add_variable(idx, nom_var, bool(val), varianttype=ua.VariantType.Boolean)
            
            # Droits d'écriture
            if props.get("writable", False):
                await var.set_writable()
                
            noeuds_crees[nom_var] = var
            
    return serveur, noeuds_crees, url