def executer_logique(entrees, memoire_interne):
    sorties = {}
    
    # --- 1. LECTURE DES ENTRÉES ---
    # Capteurs Terrain (Modbus)
    niveau = entrees.get("niveau_acide", 0.0)
    qualite = entrees.get("qualite_acide", 7.0)
    alarme_debordement = entrees.get("alarme_debordement", False)
    
    # Commandes SCADA (OPC-UA)
    en_marche = entrees.get("en_marche", False)
    mode_auto = entrees.get("mode_auto", True)
    acquittement = entrees.get("acquittement", False)
    
    # Boutons Manuels SCADA (OPC-UA)
    manu_pompe = entrees.get("manu_pompe", False)
    manu_vanne = entrees.get("manu_vanne", False)
    manu_tambour = entrees.get("manu_tambour", False)

    # --- 2. GESTION DES DÉFAUTS & SÉCURITÉS ---
    # Déclenchement : L'alarme matérielle force le défaut
    if alarme_debordement:
        memoire_interne["defaut"] = True
        
    # Acquittement : On efface le défaut SI le niveau a baissé ET que l'opérateur valide
    if memoire_interne.get("defaut", False):
        if acquittement and not alarme_debordement:
            memoire_interne["defaut"] = False

    # Verrouillage : Si un défaut est actif, TOUT est coupé (Priorité absolue)
    #if memoire_interne.get("defaut", False):
    #    return {
    #        "cmd_pompe_acide": False, "cmd_vanne_vidange": False,
    #        "cmd_moteur_tambour": False, "cmd_conv_entree": False, "cmd_conv_sortie": False
    #    }
    defaut_actif = memoire_interne.get("defaut", False)


# --- 3. SÉLECTION DU MODE DE MARCHE ---
    if mode_auto:
        # ==========================================
        # MODE AUTOMATIQUE
        # ==========================================
        
        # SÉCURITÉ : En AUTO, un défaut ou l'arrêt fige complètement le procédé
        if defaut_actif or not en_marche:
            sorties["cmd_pompe_acide"] = False
            sorties["cmd_vanne_vidange"] = False
            sorties["cmd_moteur_tambour"] = False
            sorties["cmd_conv_entree"] = False
            sorties["cmd_conv_sortie"] = False
            memoire_interne["mode_vidange"] = False 
        else:
            # --- A. Régulation du niveau (Hystérésis 40% - 80%) ---
            if niveau >= 80.0:
                sorties["cmd_pompe_acide"] = False
            elif niveau <= 40.0:
                sorties["cmd_pompe_acide"] = True
            else:
                sorties["cmd_pompe_acide"] = memoire_interne.get("cmd_pompe_acide", False)

            # --- B. Cycle de renouvellement d'acide (Qualité pH) ---
            if qualite < 5.0:
                memoire_interne["mode_vidange"] = True

            if memoire_interne.get("mode_vidange", False):
                sorties["cmd_conv_entree"] = False
                sorties["cmd_moteur_tambour"] = False
                sorties["cmd_vanne_vidange"] = True
                sorties["cmd_pompe_acide"] = False # Priorité à la purge
                
                if niveau <= 5.0:
                    memoire_interne["mode_vidange"] = False
            else:
                # Processus normal de rinçage
                sorties["cmd_vanne_vidange"] = False
                sorties["cmd_moteur_tambour"] = True
                sorties["cmd_conv_entree"] = True

            sorties["cmd_conv_sortie"] = sorties.get("cmd_moteur_tambour", True)
            
    else:
        # ==========================================
        # MODE MANUEL (Maintenance)
        # ==========================================
        # L'opérateur pilote directement, MÊME en cas de défaut (pour pouvoir dépanner)
        
        # Ultime sécurité matérielle (Interlock) : impossible de forcer la pompe si l'alarme de débordement hurle
        if manu_pompe and not alarme_debordement:
            sorties["cmd_pompe_acide"] = True
        else:
            sorties["cmd_pompe_acide"] = False
            
        sorties["cmd_vanne_vidange"] = manu_vanne
        sorties["cmd_moteur_tambour"] = manu_tambour
        
        sorties["cmd_conv_entree"] = False
        sorties["cmd_conv_sortie"] = manu_tambour

    # --- 4. MISE À JOUR DE LA MÉMOIRE ---
    memoire_interne["cmd_pompe_acide"] = sorties.get("cmd_pompe_acide", False)
    
    return sorties