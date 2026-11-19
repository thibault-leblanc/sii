# Graph Report - PLATEFORME  (2026-11-19)

## Corpus Check
- Corpus is ~28,183 words - fits in a single context window. You may not need a graph.

## Summary
- 505 nodes · 614 edges · 37 communities (22 shown, 15 thin omitted)
- Extraction: 93% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 38 edges (avg confidence: 0.89)
- Token cost: 261,371 input · 0 output

## Community Hubs (Navigation)
- Automate OPC-UA (ancien + rinçage)
- Données, rsync et audit
- Serveur IaaC et UI
- Schéma JSON (types)
- Spécifications procédé et IHM
- Netplan pi31
- Netplan pi32
- Netplan pi51
- Simulateur rinçage (cœur)
- Serveurs Modbus simulés
- UI IaaC : graphe et édition
- Schéma IaaC (sections)
- Compose API ancienne
- Compose API rinçage
- Compose test OPC-UA
- Compose serveur FTP
- Client Modbus automate
- Compose simulateur rinçage
- Compose simulateur cuve
- Compose agent HA
- Compose SCADA FUXA
- Pages IaaC (copies)
- Script installation ancien
- Chargeur images obsolète
- Sonde check_api
- Sonde check_sim
- VLAN pi31
- Docker pi31
- Test OPC-UA pi31
- VLAN pi32
- Docker pi32
- Test OPC-UA pi32
- VLAN pi51
- Docker pi51
- Modèle provisioning Ubuntu

## God Nodes (most connected - your core abstractions)
1. `RequestHandler` - 12 edges
2. `MoteurPhysique` - 10 edges
3. `Conteneur API de Rincage (192.168.30.20 / 192.168.20.20, cycle 100 ms)` - 10 edges
4. `chargerDonneesDansGraphe()` - 9 edges
5. `chargerDonneesDansGraphe()` - 9 edges
6. `AutomateModbusClient` - 8 edges
7. `principal()` - 7 edges
8. `ha-cluster` - 7 edges
9. `donnees-vlan-20` - 7 edges
10. `scada_fuxa` - 7 edges

## Surprising Connections (you probably didn't know these)
- `IHM Mode AUTOMATIQUE (Marche/Arret, Etat Cycle)` --references--> `executer_logique()`  [INFERRED]
  documentation/IHM_SCADA_Specification.pdf → configurations/conteneurs/api/rincage/logique.py
- `API (le cerveau) - cycle 100 ms` --conceptually_related_to--> `executer_logique()`  [INFERRED]
  documentation/recapitulatif_procede_api.pdf → configurations/conteneurs/api/rincage/logique.py
- `Conteneur API de Rincage (192.168.30.20 / 192.168.20.20, cycle 100 ms)` --conceptually_related_to--> `executer_logique()`  [INFERRED]
  documentation/specifications_fonctionnelles_rincage.pdf → configurations/conteneurs/api/rincage/logique.py
- `Lois de la simulation (+2.5%/s, -3.0%/s, alarme >=95%, -0.05 pH/piece)` --conceptually_related_to--> `MoteurPhysique`  [INFERRED]
  documentation/specifications_fonctionnelles_rincage.pdf → configurations/conteneurs/sim/rincage/moteur_physique.py
- `H6: risque double maitre (split-brain)` --semantically_similar_to--> `Variable VLAN_CIBLE`  [AMBIGUOUS] [semantically similar]
  documentation/audit_fonctionnel.md → configurations/conteneurs/donnees/agent-sync/readme.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Flux ingestion FTP -> replication rsync par VLAN** — configurations_conteneurs_donnees_serveur_readme_serveur_ftp, configurations_conteneurs_donnees_agent_sync_readme_agent_sync, configurations_conteneurs_donnees_readme_segregation_vlan, documentation_audit_fonctionnel_replication_par_vlan [EXTRACTED 1.00]
- **Separation plan de controle (pi51) / plan de donnees (pi3X)** — documentation_audit_fonctionnel_cluster_infra, documentation_audit_fonctionnel_cluster_fonctionnel, documentation_audit_fonctionnel_srv_sii_arborescence, documentation_audit_fonctionnel_gestionnaire_agent_noeud [EXTRACTED 1.00]
- **Topology graph rendering pipeline (vis-network)** — iaac_templates_index_chargerdonneesdansgraphe, iaac_templates_index_initialisernetwork, iaac_templates_index_appliquerfiltres, iaac_templates_index_appliquerfocus, iaac_templates_index_retirerfocus [EXTRACTED 1.00]
- **Provisioning script generation flow** — iaac_templates_index_afficherdetails, iaac_templates_index_genererprovisioning, iaac_templates_index_api_provisioning, iaac_templates_index_provisioning_modal, iaac_templates_index_telechargerscript [EXTRACTED 1.00]
- **Edit-and-persist flow to serveur.py** — iaac_templates_index_enregistrermodifications, iaac_templates_index_supprimerelement, iaac_templates_index_validerajout, iaac_templates_index_sauvegarderfichier, iaac_templates_index_api_sauvegarder [EXTRACTED 1.00]
- **Logique de controle API du rincage (hysteresis, maintenance chimique, interlocks, mode manuel)** — documentation_specifications_fonctionnelles_rincage_regulation_niveau, documentation_specifications_fonctionnelles_rincage_cycle_maintenance_chimique, documentation_specifications_fonctionnelles_rincage_interlocks, documentation_specifications_fonctionnelles_rincage_mode_manuel, configurations_conteneurs_api_rincage_logique_executer_logique [INFERRED 0.85]
- **Chaine SCADA -OPC-UA-> API -Modbus TCP-> Simulation** — documentation_specifications_fonctionnelles_rincage_supervision_scada, documentation_specifications_fonctionnelles_rincage_opc_ua, documentation_specifications_fonctionnelles_rincage_conteneur_api, documentation_specifications_fonctionnelles_rincage_modbus_tcp, documentation_specifications_fonctionnelles_rincage_conteneur_simulation [EXTRACTED 1.00]
- **Phenomenes physiques simules (hydraulique, mecanique, chimique)** — documentation_recapitulatif_procede_api_dynamique_hydraulique, documentation_recapitulatif_procede_api_dynamique_mecanique, documentation_recapitulatif_procede_api_dynamique_chimique, configurations_conteneurs_sim_rincage_moteur_physique_moteurphysique [INFERRED 0.85]

## Communities (37 total, 15 thin omitted)

### Community 0 - "Automate OPC-UA (ancien + rinçage)"
Cohesion: 0.07
Nodes (14): boucle_automate(), principal(), ClientTerrainModbus, MoteurAutomate, principal(), AutomateModbusClient, executer_logique(), initialiser_opcua() (+6 more)

### Community 1 - "Données, rsync et audit"
Cohesion: 0.05
Nodes (38): api-rincage requirements.txt, asyncua==1.1.5 (OPC-UA), pymodbus>=3.6.8 (automate), commande.sh script, deploiement_sync.sh script, Agent de Synchronisation Rsync (readme), Conteneur agent-sync (rsync/SSH, Alpine), sync.sh (boucle 60 s) (+30 more)

### Community 2 - "Serveur IaaC et UI"
Cohesion: 0.08
Nodes (22): Chargement initial (fetch infrastructure.json + schema.json), sauvegarderFichier(), RequestHandler, afficherDetails(), GET /api/data/infrastructure.json, GET /api/data/schema.json, GET /api/provisioning/<nodeId>, POST /api/sauvegarder (X-File-Target header) (+14 more)

### Community 3 - "Schéma JSON (types)"
Cohesion: 0.06
Nodes (35): properties, properties, type, type, type, type, type, type (+27 more)

### Community 4 - "Spécifications procédé et IHM"
Cohesion: 0.09
Nodes (27): Cahier des Charges IHM - Poste de Conduite SCADA, Fuxa (SCADA/HMI web), Inventaire des Widgets Fuxa (bindings OPC-UA), Layout ecran principal Fuxa - Supervision Ligne de Rincage, IHM Mode AUTOMATIQUE (Marche/Arret, Etat Cycle), IHM Mode MANUEL (Forcage Pompe/Vanne/Tambour), IHM Securite & Alarmes (Voyant Defaut Materiel, Acquittement), Description Fonctionnelle du Procede (Tambour de Rincage a l'Acide) (+19 more)

### Community 5 - "Netplan pi31"
Cohesion: 0.08
Nodes (24): addresses, dhcp4, id, link, nameservers, routes, id, link (+16 more)

### Community 6 - "Netplan pi32"
Cohesion: 0.08
Nodes (24): addresses, dhcp4, id, link, nameservers, routes, id, link (+16 more)

### Community 7 - "Netplan pi51"
Cohesion: 0.08
Nodes (24): addresses, dhcp4, id, link, nameservers, routes, id, link (+16 more)

### Community 8 - "Simulateur rinçage (cœur)"
Cohesion: 0.12
Nodes (9): principal(), MemoirePartagee, MoteurPhysique, Dynamique Mecanique (transit pieces 5s / 15s), Simulation (le terrain) - Physique du systeme, Conteneur Simulation Physique (serveur Modbus TCP, VLAN 20), Lois de la simulation (+2.5%/s, -3.0%/s, alarme >=95%, -0.05 pH/piece), Transit des pieces en file FIFO (5s entree, 15s sejour) (+1 more)

### Community 9 - "Serveurs Modbus simulés"
Cohesion: 0.11
Nodes (6): BlocDonneesSimulation, lancer_serveur_modbus(), BlocDonneesSimulation, lancer_serveur_modbus(), BlocDonneesSimulation, lancer_serveur_modbus()

### Community 10 - "UI IaaC : graphe et édition"
Cohesion: 0.12
Nodes (14): afficherDetails(), appliquerFocus(), changerVue(), chargerDonneesDansGraphe(), enregistrerModifications(), fermerDetails(), genererFormulaireAjout(), initialiserNetwork() (+6 more)

### Community 11 - "Schéma IaaC (sections)"
Cohesion: 0.12
Nodes (17): type, type, ^[a-zA-Z0-9_-]+$, properties, metadonnes, reseaux_globaux, ressources_logiques, ressources_physiques (+9 more)

### Community 12 - "Compose API ancienne"
Cohesion: 0.15
Nodes (14): build, container_name, environment, networks, restart, networks, vlan20, vlan30 (+6 more)

### Community 13 - "Compose API rinçage"
Cohesion: 0.15
Nodes (14): container_name, image, networks, restart, volumes, networks, vlan20, vlan30 (+6 more)

### Community 14 - "Compose test OPC-UA"
Cohesion: 0.15
Nodes (14): networks, vlan20, vlan30, services, test_opcua, container_name, image, networks (+6 more)

### Community 15 - "Compose serveur FTP"
Cohesion: 0.15
Nodes (13): container_name, environment, image, networks, restart, volumes, networks, reseau_macvlan (+5 more)

### Community 16 - "Client Modbus automate"
Cohesion: 0.21
Nodes (3): AutomateModbusClient, main(), test_ping()

### Community 17 - "Compose simulateur rinçage"
Cohesion: 0.18
Nodes (11): networks, vlan20, services, simulateur_acide, container_name, image, networks, restart (+3 more)

### Community 18 - "Compose simulateur cuve"
Cohesion: 0.20
Nodes (10): networks, vlan20, services, simulateur, build, container_name, networks, restart (+2 more)

### Community 19 - "Compose agent HA"
Cohesion: 0.20
Nodes (9): container_name, image, network_mode, privileged, restart, volumes, services, ha-cluster (+1 more)

### Community 20 - "Compose SCADA FUXA"
Cohesion: 0.22
Nodes (8): build, container_name, image, ports, restart, volumes, services, scada_fuxa

### Community 21 - "Pages IaaC (copies)"
Cohesion: 0.67
Nodes (3): Ontologie IaaC UI (sav, static), Ontologie IaaC UI (sav, copie identique), Ontologie IaaC UI (template servi par serveur.py)

## Ambiguous Edges - Review These
- `Variable VLAN_CIBLE` → `H6: risque double maitre (split-brain)`  [AMBIGUOUS]
  documentation/audit_fonctionnel.md · relation: semantically_similar_to
- `Cycle automatique de renouvellement chimique (pH < 5.5)` → `Cycle automatique de maintenance chimique (pH < 5.0, vidange <=5%)`  [AMBIGUOUS]
  documentation/recapitulatif_procede_api.pdf · relation: semantically_similar_to

## Knowledge Gaps
- **20 isolated node(s):** `old_cuve_pression requirements.txt (pymodbus==3.4.0)`, `Agent de Synchronisation Rsync (readme)`, `sync.sh (boucle 60 s)`, `Serveur FTP (Ingestion) readme`, `Cluster fonctionnel (pi31, pi32)` (+15 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 241 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RequestHandler` connect `Serveur IaaC et UI` to `Automate OPC-UA (ancien + rinçage)`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `RequestHandler` (e.g. with `GET /api/data/infrastructure.json` and `GET /api/data/schema.json`) actually correct?**
  _`RequestHandler` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `old_cuve_pression requirements.txt (pymodbus==3.4.0)`, `Agent de Synchronisation Rsync (readme)`, `sync.sh (boucle 60 s)` to the rest of the system?**
  _20 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Automate OPC-UA (ancien + rinçage)` be split into smaller, more focused modules?**
  _Cohesion score 0.06745098039215686 - nodes in this community are weakly interconnected._
- **Why does `executer_logique()` connect `Automate OPC-UA (ancien + rinçage)` to `Spécifications procédé et IHM`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Variable VLAN_CIBLE` and `H6: risque double maitre (split-brain)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **What is the exact relationship between `Cycle automatique de renouvellement chimique (pH < 5.5)` and `Cycle automatique de maintenance chimique (pH < 5.0, vidange <=5%)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._