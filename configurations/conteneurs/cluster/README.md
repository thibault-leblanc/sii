# Agent de haute disponibilité (`agent-ha`)

Un conteneur par nœud du cluster `fonctionnel` (pi31, pi32). Il élit un **maître** par VRRP (keepalived) sur le
VLAN10 et fait tourner l'automate et le simulateur **sur le maître seulement**. Il pilote les conteneurs du nœud
par le socket Docker (`network_mode: host`, `privileged`).

## Fichiers

| Fichier | Rôle |
|---|---|
| `Dockerfile` | Alpine figée, keepalived, client Docker, Python (lecture de la config), `arping`. |
| `scripts/entrypoint.sh` | Lit `config_cluster.json`, écrit la configuration keepalived, lance le chargeur d'images et le garde-fou, puis keepalived. |
| `scripts/check_health.sh` | Sonde : le maître est sain si **chaque** service piloté tourne. |
| `scripts/action.sh` | Transitions MASTER / BACKUP / FAULT / STOP : démarrer ou arrêter les services. |
| `scripts/garde_fou.sh` | Sans la VIP, aucun service piloté ne doit tourner : arrêt sous 20 s. |
| `scripts/auto_loader.sh` | Charge les images déposées dans `~/images` du nœud. |

Configuration : `~/config_cluster.json` du nœud, **générée depuis NetBox** (groupe VRRP `coeur-sii`, services `ha`,
priorités, IP des services). Le compose de l'agent est généré lui aussi (`~/ha-cluster/docker-compose.yml`).

## Comportement

| Situation | Réaction |
|---|---|
| Démarrage d'un nœud | Il démarre en BACKUP sans rien arrêter. Le nœud de plus forte priorité (pi31 : 100, pi32 : 90) devient maître s'il n'y en a pas. |
| Service planté sur le maître | Sonde en échec 3 fois de suite (~30 s) : le maître passe en **FAULT**, lâche la VIP et arrête ses services ; le passif devient maître. |
| Maître éteint, ou agent arrêté | L'agent arrête ses services en partant (`notify_stop`) ; le passif devient maître en 1 à 3 s. |
| Nouveau maître | Avant de démarrer, il vérifie par ARP (`arping -D`) que chaque IP de service est libre sur le terrain, et attend jusqu'à 90 s. Il ne démarre jamais un service dont l'IP répond encore ailleurs. |
| Retour de l'ancien maître | Il reste passif (`nopreempt`) : pas de reprise automatique. Retour sur pi31 : geste explicite (voir `netbox/README.md`). |
| Doublon quelle qu'en soit la cause | Le garde-fou du nœud sans VIP arrête ses services en moins de 20 s. |

L'automate et le simulateur sont en `restart: "no"` et **créés d'avance** sur les deux nœuds
(`docker compose create`) : l'agent ne fait que `docker start` / `docker stop`. Après chaque bascule, le procédé
repart à froid : relancer « Marche » dans le SCADA.

## Pourquoi ces choix (incidents et audit)

| Mécanisme | Raison |
|---|---|
| Dossier `/etc/keepalived` créé dans l'image | Absent du paquet Alpine : l'agent n'avait **jamais** pu démarrer (2026-11-22). |
| Premier BACKUP du démarrage sans arrêt | Sinon, redémarrer l'agent coupait le procédé du maître (audit, constat n°3). |
| Transitions sérialisées (verrou, dernier état voulu) | keepalived lance les scripts en parallèle : un `docker start` lent finissait après le `docker stop` suivant → doublon d'IP (2026-11-22). |
| FAULT au lieu d'une baisse de priorité | Avec `nopreempt`, une priorité baissée (80) n'autorise pas le passif (90) à prendre la main : une panne de service ne basculait pas (2026-11-23). |
| Contrôle ARP avant démarrage | Le nouveau maître démarrait avant que l'ancien ait fini d'arrêter : doublon de quelques secondes (2026-11-23, audit H6). |
| `notify_stop` + `stop_grace_period: 30s` | L'arrêt de l'agent laissait tourner les services pendant que le passif démarrait les siens. |
| `nopreempt` | Évite les allers-retours (deux redémarrages à froid) et les bascules en boucle (audit H2). |
| Sonde `interval 10 / timeout 8 / fall 3` | Un Pi 3B chargé dépassait les délais : bascules intempestives. |
| Chargeur limité à `~/images` | Un `.tar` déposé par FTP pouvait remplacer une image (audit, constat n°1). |

Le détail des tests (scénarios rejoués en image puis sur les nœuds) est dans `documentation/journal_exploitation.md`.

## Construire et déployer

```sh
sh configurations/construire_images.sh agent-ha
# puis, sur le passif d'abord puis sur le maître (bascule contrôlée) :
scp configurations/images/agent-ha.tar piXX@...:images/ && ssh piXX@... 'docker load -i ~/images/agent-ha.tar && cd ~/ha-cluster && docker compose up -d'
```

Tester sans les Pi : construire l'image en local et lancer les scripts avec un faux `docker` (voir les scénarios
du journal, 2026-11-22 et 2026-11-23).
