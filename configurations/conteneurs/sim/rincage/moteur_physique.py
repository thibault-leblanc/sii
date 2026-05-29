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
        
        # --- NOUVEAUTÉ : Dissociation du Volume (physique) et du Niveau (capteur) ---
        # On définit une capacité max arbitraire pour la cuve (ex: 1000 Litres = 100%)
        # On initialise à 0 volume.
        self.volume_reel = 0.0
        self.capacite_max = 1000.0
        
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

            # --- 2. DYNAMIQUE HYDRAULIQUE (Volume Réel) ---
            
            # La physique de base : si la pompe tourne, le volume d'eau monte
            # (On ne bloque plus le remplissage, ça peut déborder !)
            if pompe:
                # Calcul : Le débit en %/sec doit être transformé en Litres/sec
                # (1% de 1000L = 10L)
                litres_entrants = (self.config["debit_pompe_pourcent_sec"] / 100.0) * self.capacite_max
                self.volume_reel += litres_entrants * dt
                
            # Si la vanne est ouverte, le volume descend par gravité
            if vanne and self.volume_reel > 0.0:
                litres_sortants = (self.config["debit_vanne_pourcent_sec"] / 100.0) * self.capacite_max
                self.volume_reel -= litres_sortants * dt
            
            # Contrainte physique absolue : pas de volume négatif
            self.volume_reel = max(0.0, self.volume_reel)
            
            # --- 3. LECTURE DES CAPTEURS (Envoyés à l'API) ---
            # Le capteur de niveau plafonne à 100% mécaniquement
            niveau_capteur = (self.volume_reel / self.capacite_max) * 100.0
            niveau_capteur_bloque = min(100.0, niveau_capteur) # Sature à 100%
            
            self.memoire.set("niveau_acide", niveau_capteur_bloque)
            
            # L'alarme (flotteur haut) s'active dès que le capteur voit >= 95%
            debordement_actuel = niveau_capteur_bloque >= 95.0
            debordement_precedent = self.memoire.get("alarme_debordement")
            if debordement_actuel and not debordement_precedent:
                logger.warning(f"⚠️ DÉBORDEMENT PHYSIQUE DÉTECTÉ (Volume réel : {self.volume_reel:.1f}L)")
            self.memoire.set("alarme_debordement", debordement_actuel)

            # --- 4. DYNAMIQUE MÉCANIQUE ET CHIMIQUE ---
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