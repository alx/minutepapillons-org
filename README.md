# Minute papillons — static site (Hugo)

Static Hugo build of https://www.minutepapillons.org — the 6 pages of the live site:

- `/` (accueil)
- `/220-2/`
- `/louez-moi/`
- `/trouver-nos-cabines/`
- `/on-parle-de-votre-projet/`
- `/questions-frequentes/`

## Layout

- `hugo.toml`, `content/`, `layouts/`, `static/` — Hugo source
- `public/` — built site (served as-is; `hugo build` regenerates it here)
- `build_hugo.py` — original converter from the WordPress mirror (provenance).
  It expects the WP mirror checkout next to it and outputs to `./hugo/`; the
  mirror is archived in `../minutepapillons-wp-mirror-*.tar.gz`. Do not run it
  without the mirror extracted.

## Build

```sh
hugo build        # from this directory → public/
```
