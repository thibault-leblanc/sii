import time
import threading

class SimulateurEntreesSorties:
    def __init__(self):
        self.variables = {
            "niveau": 0.0,
            "temperature": 20.0,
            "vanne_remplissage": False,
            "chauffage": False,
            "pompe_vidange": False
        }
        self.en_fonctionnement = True
        self.thread = threading.Thread(target=self._boucle_physique, daemon=True)
        self.thread.start()

    def _boucle_physique(self):
        while self.en_fonctionnement:
            if self.variables["vanne_remplissage"] and self.variables["niveau"] < 100.0:
                self.variables["niveau"] += 2.5
            if self.variables["pompe_vidange"] and self.variables["niveau"] > 0.0:
                self.variables["niveau"] -= 3.0
                
            if self.variables["chauffage"] and self.variables["niveau"] > 10.0:
                self.variables["temperature"] += 1.2
            else:
                if self.variables["temperature"] > 20.0:
                    self.variables["temperature"] -= 0.3

            self.variables["niveau"] = max(0.0, min(100.0, self.variables["niveau"]))
            self.variables["temperature"] = max(20.0, min(100.0, self.variables["temperature"]))
            time.sleep(1.0) 

    def arreter(self):
        self.en_fonctionnement = False
        self.thread.join()