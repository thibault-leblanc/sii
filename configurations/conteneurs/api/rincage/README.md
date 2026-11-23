# Automate logiciel du rinçage (`api-rincage`)

Automate écrit en Python (asyncio). Toutes les 100 ms : il **lit le terrain** (Modbus TCP, client du simulateur
192.168.20.10:502), **lit les ordres de conduite** (son serveur OPC-UA), **exécute la logique**, **écrit les
actionneurs** (Modbus) et **publie l'état** (OPC-UA, pour le SCADA).

| Réseau | IP | Usage |
|---|---|---|
| VLAN20 (terrain) | 192.168.20.20 | Client Modbus TCP vers le simulateur |
| VLAN30 (supervision) | 192.168.30.20 | Serveur OPC-UA `opc.tcp://192.168.30.20:4840`, sans sécurité (audit de sécurité à venir) ; **route par défaut** (`gw_priority`) |

## Fichiers

| Fichier | Rôle |
|---|---|
| `app.py` | Boucle de scrutation (lecture, logique, écriture, publication), arrêt propre sur SIGTERM. |
| `logique.py` | **Logique de conduite**, fonction pure `executer_logique(entrees, memoire)` : testée dans `tests/test_procede.py`. |
| `client_modbus.py` | Lecture des entrées (DI 10-12, IR 20-21) et écriture des bobines 0-4. |
| `serveur_opcua.py` | Crée les variables OPC-UA depuis `opcua_mapping`. |
| `config_api.json` | Cycle, cible Modbus, serveur OPC-UA, variables exposées. **Déployée depuis le repo** à chaque publication (référencée dans NetBox). |
| `requirements.txt` | `pymodbus==3.16.2` (API `device_id=`), `asyncua==1.1.5`, versions figées. |

## Logique de conduite (`logique.py`)

- **Repli de sécurité** : si une mesure terrain manque (lecture Modbus incomplète ou coupée), **toutes les sorties
  sont coupées** (avant : niveau absent = 0 % → pompe en marche).
- **Automatique** (`ModeAuto`), avec `EnMarche` :
  - niveau régulé entre 40 et 80 % (hystérésis sur la pompe) ;
  - pH < 5 : **purge** (vanne ouverte, production arrêtée) jusqu'à 5 % de niveau, puis **remplissage en acide
    neuf** jusqu'à 80 % sans tester le pH, puis reprise (sans cette phase, la purge repartait aussitôt, audit P1) ;
  - production : convoyeurs et tambour en marche.
- **Défaut débordement** (alarme du simulateur à 95 %) : tout est coupé en automatique ; acquittement
  (`AcquittementDefaut`) possible seulement quand l'alarme a disparu.
- **Manuel** : commandes directes (`ManuPompe`, `ManuVanne`, `ManuTambour`), pompe interdite si débordement.

## Variables OPC-UA (espace `http://usine.automate.local`)

| Dossier | Variables | Sens |
|---|---|---|
| `Systeme` | `EnMarche`, `ModeAuto`, `AcquittementDefaut` | écriture (SCADA → automate) |
| `Systeme` | `Defaut`, `ConnexionSimuOk`, `TempsCycleReelMs` | lecture |
| `Commandes_Manuelles` | `ManuPompe`, `ManuVanne`, `ManuTambour` | écriture |
| `Cuve` | `NiveauAcide` (%), `QualiteAcide` (pH), `PompeActive`, `VanneActive` | lecture |
| `Mecanique` | `TambourTourne`, `ConvoyeurEntree`, `ConvoyeurSortie` | lecture |

Les identifiants de nœuds (`ns=2;i=N`) dépendent de l'ordre de `opcua_mapping` : le projet FUXA les utilise.
**Ne pas réordonner** ce mapping sans mettre à jour le projet SCADA.

## Exploitation

Service HA (`restart: "no"`) : démarré par l'agent HA sur le maître seulement. Après une modification du code,
reconstruire l'image (`sh configurations/construire_images.sh api-rincage`) et la déployer (`netbox/README.md`).
Écarts connus avec la spécification : défaut en mode manuel (P2), acquittement sur niveau et non sur front (P3),
état de cycle non exposé (P4) — voir l'audit.
