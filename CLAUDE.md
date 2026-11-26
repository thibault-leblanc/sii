# Plateforme SII : règles permanentes

Tu connais le projet. Ces règles reprennent les pratiques suivies depuis le début : les maintenir à chaque
intervention. En cas de contradiction entre un document et le projet réel (plateforme et dépôt git), **le réel fait
foi** : signaler l'écart, l'inscrire, ne pas « corriger » le réel pour coller au document.

- Cible et modèle de déploiement : `documentation/architecture_reference.md`
- Chantier en cours : `documentation/modop_chaine_livraison.md`

## Contexte à jour

- **graphify** : interroger le graphe (`graphify query "<question>"`) avant de parcourir les fichiers ; le mettre à
  jour après les changements, documentation comprise. Le graphe oriente, le fichier et la plateforme font foi.
  `graphify-out/` reste hors git.
- Début d'intervention : dernières entrées du journal d'exploitation.

## Internet

La coupure se prépare. D'ici là, dans cet ordre : 1. ressource locale de la plateforme ; 2. passage par le poste
d'administration si c'est simple ; 3. accès direct depuis la plateforme, **seulement si indispensable**. Les cas 2 et
3 sont inscrits au registre des dépendances (modop, §2).

## Règles

0. **Sobriété** : la solution la plus simple qui répond au besoin. Pas d'outil, de service, d'abstraction ou de
   document non demandé ; changements limités au sujet traité ; textes courts et factuels. Une idée hors périmètre se
   propose dans le compte rendu.
1. **NetBox d'abord** : migration datée et relançable, puis `python netbox/outils/synchro.py`, relecture du diff.
   Ne jamais éditer un fichier généré, ni lancer `importer.py` sur l'instance en service.
2. **Modèle type** : toute brique a sa fiche, sa classe de déploiement et suit le cycle de vie. Un écart à
   l'architecture est signalé et inscrit au §7 de la référence.
3. **Diagnostic en lecture seule** avant modification.
4. **Validation de l'administrateur** avant : `sudo`, netplan, pare-feu, redémarrage, bascule, « Marche »,
   suppression, `git push`, décision d'architecture.
5. **HA** : passif d'abord ; `create` seulement sur l'automate et le simulateur ; jamais deux nœuds actifs ; passif en
   échec, on ne touche pas au maître.
6. **Non-régression** : référence relevée avant le changement, mêmes contrôles après (modop, §4). Tout outil modifié
   a son test. Un contrôle en échec ou non joué bloque la clôture : corriger ou revenir en arrière, et le dire. Ne
   jamais affaiblir un test pour le faire passer.
7. **Versions figées**, pas de `latest`. Fins de ligne selon `.gitattributes`.
8. Manque de sécurité **assumé** jusqu'à la GIA : ne pas ajouter d'authentification ou de TLS de sa propre
   initiative. Secrets hors de git.
9. **Tracer** : journal (heure UTC, nœud, action, résultat), incidents et erreurs compris ; suivi d'audit (§10).
10. **Ranger** : README de chaque dossier à jour dans le même commit ; ni artefact, ni copie manuelle, ni fichier
    temporaire dans git.
11. **Commits propres** : un sujet par commit, en français, « Sujet : ce qui change », corps en puces (quoi,
    pourquoi, vérifications), ligne `Co-Authored-By` conservée. Garde-fou actif avec `NETBOX_URL` et `NETBOX_TOKEN`
    définis ; pas de `--no-verify` sans accord.
12. **Compte rendu** : fait, vérifié sur la plateforme, testé hors ligne, supposé, décisions attendues.

## Repères pratiques

- **Accès** : Git Bash sur le poste d'administration (192.168.1.26, côté WAN du pare-feu) ; `ssh <nœud>@<IP>` par clé
  (pi31 .10.10, pi32 .10.11, pi51 .10.12) ; NetBox sur `http://localhost:8000` (`netbox-docker`, cloné hors du dépôt,
  à relancer si Docker Desktop s'est arrêté). Garde-fou : `git config core.hooksPath .githooks`.
- **Contrôles** : `python netbox/outils/synchro.py [--verifier]` ; `ssh <nœud>@<IP> sh -s < netbox/outils/collecte.sh
  > netbox/collecte/<nœud>.json` puis `python netbox/outils/derive.py netbox/collecte/` ;
  `python tests/plateforme/verifier_chaine_scada.py [--marche]`.
- **Fichiers générés** : `configurations/machines/<nœud>/` (versionnés) et `netbox/genere/` (hors git) ; publication
  par `netbox/genere/publier.sh`.
- **Pièges connus** :
  - sous Windows, un script Python passé sur l'entrée standard corrompt les accents : écrire un fichier ;
  - `journalctl --since` est en heure locale (CET), le journal d'exploitation en UTC ;
  - pfSense filtre à l'**entrée** : le trafic du poste d'administration est réglé sur l'onglet WAN ;
  - redémarrer l'agent HA d'un nœud arrête ses services (voulu) ; ne jamais `restart` Docker sur un nœud actif.
