# Mises à jour des paquets (`machines/apt/`)

`20auto-upgrades` désactive les mises à jour automatiques d'Ubuntu sur les nœuds. Le 2026-11-23, elles ont mis à
jour Docker et containerd, redémarré le moteur de conteneurs, donc relancé l'automate à froid, et saturé un
Pi 3B pendant 40 min.

Application (faite sur pi31, pi32 et pi51 le 2026-11-23) :

```sh
sudo install -m 644 20auto-upgrades /etc/apt/apt.conf.d/
sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer unattended-upgrades
```

Les mises à jour se font désormais à la main, nœud passif d'abord (voir [`../README.md`](../README.md)).
