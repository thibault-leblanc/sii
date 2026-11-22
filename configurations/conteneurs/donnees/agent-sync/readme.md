# 🔄 Agent de synchronisation rsync

Réplique en continu le dossier de données d'un VLAN, depuis `pi51`, vers les nœuds du cluster fonctionnel
(`pi31`, `pi32`). Image Alpine avec `rsync` et un client SSH.

## Fonctionnement

* **Boucle** : `sync.sh` lance une synchronisation toutes les 60 s, vers chaque nœud l'un après l'autre.
* **Source en lecture seule** : le dossier du VLAN est monté en `:ro` sur `/donnees`.
* **Cible** : `/home/<nœud>/donnees/$VLAN_CIBLE/donnees/`. Une seule image sert pour tous les VLAN.
* **Garde-fous** (2026-11) :
  * source vide ou absente : synchro suspendue (avec `--delete`, elle viderait les répliques) ;
  * `ConnectTimeout=5` : un nœud éteint ne bloque pas la synchro de l'autre.

Incident du 2026-11-22 : l'image déployée depuis juin avait `vlan20` écrit en dur. L'agent du VLAN30
synchronisait donc son dossier vide vers le dossier VLAN20 des nœuds, et l'effaçait à chaque cycle. Toujours
reconstruire l'image depuis ce dossier (`configurations/construire_images.sh`) après une modification.

## Déploiement

Le compose est généré depuis NetBox (`netbox/README.md`). Construction de l'image :

```bash
sh configurations/construire_images.sh agent-sync
```

La clé SSH de `pi51` (`~/.ssh/id_rsa`) est montée en lecture seule. Sa clé publique doit figurer dans
`~/.ssh/authorized_keys` de chaque nœud cible (à refaire après la réinstallation d'un nœud).
