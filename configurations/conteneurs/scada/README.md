# SCADA de conduite (`scada`, FUXA 1.3.3)

IHM web de conduite du procédé, client OPC-UA de l'automate. Cluster `conduite` (pi51 ; pi52 à venir).

| | |
|---|---|
| Interface | http://192.168.30.10:1881 (depuis le poste d'administration : route par le pare-feu) |
| Réseau | VLAN30, IP 192.168.30.10 (macvlan), dossier `~/scada` sur pi51 |
| Connexion procédé | `OPCUA_RINCAGE` → `opc.tcp://192.168.30.20:4840`, 16 variables (même VLAN : pas de pare-feu traversé) |
| Authentification | **désactivée** (`secureEnabled: false`) : à traiter avec l'audit de sécurité |

## Fichiers

| Fichier | Rôle |
|---|---|
| `Dockerfile` | `frangoteam/fuxa:1.3.3` (version du projet validé) + pilotes `node-opcua`, `modbus-serial` figés. |
| `donnees/project.fuxap.db` | **Projet FUXA de référence** (vues, équipements, variables). |
| `donnees/settings.js`, `donnees/mysettings.json` | Réglages du serveur et de l'IHM. |

Les fichiers de `donnees/` sont déclarés dans NetBox en **amorçage** : déposés dans `~/scada/appdata` **seulement
s'ils sont absents**. Ensuite, le projet vit dans FUXA (modifications faites dans l'éditeur, alarmes, historiques)
et n'est jamais écrasé par une publication.

## Faire évoluer le projet

1. Modifier le projet dans l'éditeur FUXA (http://192.168.30.10:1881/editor).
2. Le rapatrier comme nouvelle référence versionnée :
   ```sh
   scp pi51@192.168.10.12:scada/appdata/project.fuxap.db configurations/conteneurs/scada/donnees/
   git add configurations/conteneurs/scada/donnees/project.fuxap.db && git commit
   ```
3. Pour **imposer** la référence du repo sur pi51 (écrase le projet en place) : arrêter le conteneur, supprimer
   `~/scada/appdata/project.fuxap.db`, republier (`publier.sh --appliquer`), redémarrer.

## Vérifier

```sh
python tests/plateforme/verifier_chaine_scada.py            # remontée des mesures
python tests/plateforme/verifier_chaine_scada.py --marche   # + commande « Marche » contrôlée sur le simulateur
```

## Points connus

- Le projet contient aussi `MBTCP_RINCAGE`, une connexion **Modbus directe vers le simulateur** (192.168.20.10)
  qui court-circuite l'automate (audit P6). Gardée à la demande (projet fonctionnel, amélioration plus tard) ;
  le pare-feu l'autorise (VLAN30 → VLAN20 ouvert).
- Pas encore de haute disponibilité : elle viendra avec pi52 (seconde instance VRRP pour le cluster `conduite`).
- `configurations/conteneurs/scada-dev/` est l'instance de **développement** du poste d'administration (essais),
  pas la référence.
