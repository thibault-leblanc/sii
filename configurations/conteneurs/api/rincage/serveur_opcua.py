from asyncua import Server, ua

async def initialiser_opcua(config):
    serveur = Server()
    await serveur.init()

    conf_opcua = config.get("opcua_server", {})
    bind_ip = conf_opcua.get("bind_ip", "0.0.0.0")
    endpoint_ip = conf_opcua.get("endpoint_ip", "192.168.30.20")
    port = conf_opcua.get("port", 4840)
    nom_serveur = config.get("plc_settings", {}).get("name", "API_Generic")
    
    # On bind sur 0.0.0.0 pour éviter les crashs Macvlan, mais on diffuse l'IP SCADA
    serveur.set_endpoint(f"opc.tcp://{endpoint_ip}:{port}/freeopcua/server/")
    serveur.set_server_name(nom_serveur)
    serveur.set_security_policy([ua.SecurityPolicyType.NoSecurity])

    idx = await serveur.register_namespace(conf_opcua.get("namespace", "http://default.local"))
    objet_racine = await serveur.nodes.objects.add_object(idx, nom_serveur)
    
    noeuds_crees = {}
    for nom_dossier, variables in config.get("opcua_mapping", {}).items():
        dossier = await objet_racine.add_object(idx, nom_dossier)
        for nom_var, props in variables.items():
            val = props["initial"]
            if props["type"] == "Double":
                var = await dossier.add_variable(idx, nom_var, float(val), varianttype=ua.VariantType.Double)
            else:
                var = await dossier.add_variable(idx, nom_var, bool(val), varianttype=ua.VariantType.Boolean)
            #gestion des droit d'écriture sur les variables
            if props.get("writable", False):
                await var.set_writable()

            noeuds_crees[nom_var] = var
            
    return serveur, noeuds_crees