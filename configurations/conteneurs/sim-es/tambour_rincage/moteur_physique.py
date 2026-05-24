import time
import threading
import logging

logger = logging.getLogger("SimuPhysique")

class MoteurPhysique:
    def __init__(self, memoire, config_physique):
        self.memoire = memoire
        self.config = config_physique
        self.en_fonctionnement = True
        self.file_pieces = [] # Stocke les temps de transit des pièces dans le tambour
        self.temps_piece_entree = 0.0
        
        # Le thread tourne en tâche de fond (daemon)
        self.thread = threading.Thread(target=self._boucle_physique, daemon=True)

    def demarrer(self):
        logger.info("Démarrage du moteur physique (Résolution : 1 sec)...")
        self.thread.start()

    def _boucle_physique(self):
        dt = 1.0 # Le temps avance d'une seconde à chaque boucle
        
        while self.en_fonctionnement:
            # --- 1. LECTURE DES ACTIONNEURS (Imposés par l'API) ---
            pompe = self.memoire.get("cmd_pompe_acide")
            vanne = self.memoire.get("cmd_vanne_vidange")
            conv_in = self.memoire.get("cmd_conv_entree")
            tambour = self.memoire.get("cmd_moteur_tambour")
            conv_out = self.memoire.get("cmd_conv_sortie")

            # --- 2. DYNAMIQUE HYDRAULIQUE ---
            niveau = self.memoire.get("niveau_acide")
            
            # La physique de base : si la pompe tourne, le niveau monte
            if pompe and niveau < 100.0:
                niveau += self.config["debit_pompe_pourcent_sec"] * dt
            # Si la vanne est ouverte, le niveau descend par gravité
            if vanne and niveau > 0.0:
                niveau -= self.config["debit_vanne_pourcent_sec"] * dt
            
            # Contraintes physiques : la cuve ne peut pas être à < 0% ou > 100%
            niveau = max(0.0, min(100.0, niveau))
            self.memoire.set("niveau_acide", niveau)
            
            # Le flotteur physique s'active si le niveau atteint 95%
            debordement_actuel = niveau >= 95.0
            debordement_precedent = self.memoire.get("alarme_debordement")
            if debordement_actuel and not debordement_precedent:
                logger.warning(f"⚠️ DÉBORDEMENT PHYSIQUE DÉTECTÉ (Niveau : {niveau:.1f}%)")
            self.memoire.set("alarme_debordement", debordement_actuel)

            # --- 3. DYNAMIQUE MÉCANIQUE ET CHIMIQUE ---
            qualite = self.memoire.get("qualite_acide")
            
            # Réinitialisation des capteurs de passage (impulsions)
            self.memoire.set("detec_piece_entree", False)
            self.memoire.set("detec_piece_sortie", False)

            # A. Entrée des pièces : Si le convoyeur tourne, une pièce arrive toutes les 5s
            if conv_in:
                self.temps_piece_entree += dt
                if self.temps_piece_entree >= 5.0:
                    self.file_pieces.append(self.config["temps_transit_piece_sec"])
                    self.memoire.set("detec_piece_entree", True)
                    logger.debug("Nouvelle pièce sale entrée dans le tambour.")
                    self.temps_piece_entree = 0.0
            else:
                self.temps_piece_entree = 0.0

            # B. Transit dans le tambour
            if tambour:
                nouvelle_file = []
                for temps_restant in self.file_pieces:
                    temps_restant -= dt
                    
                    if temps_restant <= 0:
                        # La pièce a fini son temps de traitement
                        if conv_out:
                            # Elle sort car le tapis d'évacuation tourne
                            self.memoire.set("detec_piece_sortie", True)
                            qualite -= self.config["degradation_ph_par_piece"]
                            logger.debug(f"Pièce évacuée. Nouvelle qualité acide : {qualite:.2f}")
                        else:
                            # Elle reste bloquée devant la sortie (Bourrage physique)
                            nouvelle_file.append(0)
                    else:
                        # La pièce continue d'avancer
                        nouvelle_file.append(temps_restant)
                self.file_pieces = nouvelle_file
            
            # Limites physiques du pH (0 = acide pur, 14 = basique)
            qualite = max(0.0, min(14.0, qualite))
            self.memoire.set("qualite_acide", qualite)

            # L'horloge du moteur physique
            time.sleep(dt)

    def arreter(self):
        self.en_fonctionnement = False
        self.thread.join()