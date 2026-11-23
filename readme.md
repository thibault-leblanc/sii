# Plateforme SII — banc de test d'un Système d'Information Industriel

Plateforme de laboratoire sur Raspberry Pi : un **procédé industriel simulé** (tambour de rinçage à l'acide),
piloté par un **automate logiciel**, supervisé par un **SCADA**, en **haute disponibilité**, sur un réseau
segmenté par **VLAN** derrière un pare-feu. Elle sert de socle pour tester des briques de SI industriel
(segmentation, supervision, données, sécurité OT…).

L'infrastructure est décrite dans **NetBox (source de vérité)** ; tous les fichiers de déploiement en sont
**générés**. Rien ne se configure à la main sur les nœuds sans passer par ce circuit.

## Architecture

```text
                    Poste d'administration (192.168.1.26, côté WAN) — NetBox, construction des images
                                               │
                                   Pare-feu pfSense (WAN 192.168.1.200)
                 ┌─────────────────────────────┼─────────────────────────────┐
        VLAN10 Administration           VLAN20 Terrain (Modbus)        VLAN30 Supervision (OPC-UA)
        192.168.10.0/24                 192.168.20.0/24                192.168.30.0/24
                 │                             │                             │
   ┌─────────────┴──────────────┐              │                             │
   pi31 (.10)  pi32 (.11)  pi51 (.12)          │                             │
   └─ cluster « fonctionnel » ─┘              │                             │
       VIP VRRP 192.168.10.251    simulateur 20.10 ◄─Modbus── automate 20.20 / 30.20 ──OPC-UA──► SCADA 30.10
       (agent HA)                 FTP 20.30, sync 20.31                      FTP 30.30, sync 30.31 (pi51)
                                  └──────── pi51 : clusters « infra » (données) et « conduite » (SCADA) ────────┘
```

| Cluster | Nœuds | Services | Rôle |
|---|---|---|---|
| `fonctionnel` | pi31 (maître nominal), pi32 | automate `api-rincage`, simulateur `sim-rincage`, agent HA | Le procédé, en haute disponibilité (VRRP) |
| `infra` | pi51 | FTP et agents rsync par VLAN | Source unique des données, répliquées vers le cluster fonctionnel |
| `conduite` | pi51 (pi52 à venir) | SCADA FUXA | Conduite du procédé (IHM web http://192.168.30.10:1881) |

Chaîne de conduite : **SCADA → OPC-UA → automate → Modbus TCP → simulateur** (et retour des mesures).

## Plan du dépôt

| Dossier | Contenu |
|---|---|
| [`netbox/`](netbox/README.md) | **Source de vérité et outillage IaC** : export du modèle, générateur, publication, collecte et contrôle de dérive, migrations NetBox, runbook d'exploitation. |
| [`iaac/`](iaac/readme.md) | IaC historique et son interface web (vue graphique interactive), **synchronisée depuis NetBox**, enrichissable à la main. |
| [`configurations/`](configurations/README.md) | Code et images des conteneurs (automate, simulateur, agent HA, SCADA, données) ; **un dossier par nœud** (`machines/<nœud>/`, généré depuis NetBox : tout ce qui y est déployé, et sa fiche). |
| [`tests/`](tests/README.md) | Tests du procédé (hors ligne) et vérification de bout en bout sur la plateforme. |
| [`documentation/`](documentation/README.md) | Spécifications, audit et son suivi, **journal d'exploitation**, schéma d'architecture. |

## Prise en main

Prérequis sur le poste d'administration : Git Bash, Python 3.11+, Docker Desktop, accès SSH par clé aux nœuds.

```sh
pip install -r netbox/outils/requirements.txt      # pynetbox, pyyaml
git config core.hooksPath .githooks                # garde-fou de commit (repo à jour avec NetBox, tests verts)
export NETBOX_URL=http://localhost:8000 NETBOX_TOKEN='nbt_...'
python netbox/outils/synchro.py                    # NetBox -> sii.yaml -> iaac/ -> génération -> tests
```

| Je veux… | Voir |
|---|---|
| Comprendre et modifier l'infrastructure | [netbox/README.md](netbox/README.md), « Modifier la plateforme » |
| Basculer, réinstaller un nœud, mettre à jour un agent | [netbox/README.md](netbox/README.md), « Exploitation courante » |
| Comprendre la haute disponibilité | [configurations/conteneurs/cluster/README.md](configurations/conteneurs/cluster/README.md) |
| Vérifier que tout fonctionne | `python netbox/outils/derive.py netbox/collecte/` et `python tests/plateforme/verifier_chaine_scada.py` |
| Savoir ce qui a été fait et pourquoi | [documentation/journal_exploitation.md](documentation/journal_exploitation.md) |

## Règles de fonctionnement

1. **NetBox d'abord** : toute modification d'infrastructure se fait dans NetBox (interface ou migration datée dans
   `netbox/migrations/`), puis `synchro.py`, publication, contrôle (`derive.py` doit donner 0 écart).
2. **Tout est versionné** : code, Dockerfile (versions figées), configurations des applications, projet SCADA,
   export du modèle. Les secrets ne le sont pas (fichiers `.env` sur les nœuds).
3. **Chaque intervention est tracée** dans le journal d'exploitation.
4. **Pas de mise à jour automatique** sur les nœuds : une mise à jour redémarre Docker, donc le procédé.
