# Hooks git du dépôt (`.githooks/`)

| Hook | Rôle |
|---|---|
| `pre-commit` | **Garde-fou** : lance `python netbox/outils/synchro.py --verifier`. Refuse le commit si `netbox/donnees/sii.yaml` diverge de NetBox, si `iaac/infrastructure.json` n'est pas à jour, si le modèle est invalide ou si un test échoue. |

Activation, une fois par clone : `git config core.hooksPath .githooks`.

NetBox n'est comparé que si `NETBOX_URL` et `NETBOX_TOKEN` sont définis. Sinon, les contrôles hors ligne sont
faits et un avertissement s'affiche. Contournement exceptionnel, en connaissance de cause : `git commit --no-verify`.
