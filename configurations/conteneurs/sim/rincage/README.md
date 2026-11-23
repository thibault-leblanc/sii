# Simulateur du tambour de rinçage (`sim-rincage`)

Simule l'usine : une cuve d'acide, une pompe, une vanne de vidange, un tambour et deux convoyeurs. Il expose ses
entrées-sorties en **serveur Modbus TCP** (192.168.20.10:502, VLAN20) ; il ne décide rien, il applique les ordres
de l'automate et calcule la physique chaque seconde.

## Fichiers

| Fichier | Rôle |
|---|---|
| `app.py` | Démarre la physique (thread) et le serveur Modbus. |
| `moteur_physique.py` | Physique, une méthode `pas(dt)` testable : volume, niveau, pH, pièces. |
| `serveur_modbus.py` | Bloc de données Modbus branché sur la mémoire partagée, selon `modbus_mapping`. |
| `memoire_partagee.py` | État partagé (verrou) entre physique et Modbus. |
| `config_simu.json` | Carte Modbus, paramètres physiques, état initial. **Déployée depuis le repo** (référencée dans NetBox). |
| `requirements.txt` | `pymodbus==3.4.0`, figé : l'API serveur utilisée (`ModbusSlaveContext`) a disparu en 3.10 (migration à faire avant pymodbus v4). |

## Carte Modbus

| Type | Adresses | Contenu |
|---|---|---|
| Bobines (écrites par l'automate) | 0 à 4 | convoyeur d'entrée, tambour, convoyeur de sortie, pompe, vanne |
| Entrées TOR | 10, 11, 12 | détection pièce en entrée, en sortie, alarme débordement (≥ 95 %) |
| Registres d'entrée | 20, 21 | niveau × 10 (%), pH × 100 |

## Physique (`physics_parameters`)

- Pompe : +2,5 %/s ; vanne : −3 %/s ; capacité 1000 l ; niveau initial = `initial_state.niveau_acide` (audit P7).
- Une pièce entre toutes les 5 s (convoyeur d'entrée), traverse le tambour en 15 s, sort si le convoyeur de sortie
  tourne (sinon bourrage) ; chaque pièce sortie dégrade le pH de 0,05.
- L'acide neuf (`ph_acide_neuf`, 7,0) se **mélange** à l'acide en place : c'est ce qui régénère le pH (audit P1).

Le procédé complet (simulateur + logique de l'automate, 4 h simulées) est testé dans `tests/test_procede.py`.
Service HA (`restart: "no"`), démarré par l'agent HA sur le maître seulement.
