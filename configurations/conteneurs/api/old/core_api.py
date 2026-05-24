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