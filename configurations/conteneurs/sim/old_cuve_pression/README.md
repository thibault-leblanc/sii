# Archive : premier simulateur, cuve chauffée (`sim/old_cuve_pression/`)

**Non déployé.** Simulateur d'une cuve (niveau, température ; vanne de remplissage, chauffage, pompe de vidange)
exposé en Modbus, piloté par le prototype [`../../api/old/`](../../api/old/README.md).

| Fichier | Contenu |
|---|---|
| `core_simulation.py` | Physique de la cuve (thread). |
| `serveur_modbus.py` | Serveur Modbus. |
| `app.py`, `Dockerfile`, `docker-compose.yml`, `requirements.txt` | Lancement. |

Remplacé par le simulateur du rinçage ([`../rincage/`](../rincage/README.md)). Candidat à la suppression.
