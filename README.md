# Minute papillons — static site (Hugo)

Static Hugo build of https://www.minutepapillons.org — the 6 pages of the live site,
in French (default language, at the site root) and English (under `/en/`):

- `/` (accueil) → `/en/` (home)
- `/220-2/` → `/en/220-2/`
- `/louez-moi/` → `/en/louez-moi/`
- `/trouver-nos-cabines/` → `/en/trouver-nos-cabines/`
- `/on-parle-de-votre-projet/` → `/en/on-parle-de-votre-projet/`
- `/questions-frequentes/` → `/en/questions-frequentes/`

## Multilingual (FR / EN)

- Content lives in `content/fr/` and `content/en/` (Hugo per-language content dirs).
- `hugo.toml` declares both languages: FR is `defaultContentLanguage` (weight 1,
  served at the root) and EN is weight 2 (served under the `/en/` language
  subdirectory).
  **NB (Hugo ≥ 0.159):** `languages.*.contentDir` is relative to the *project*
  root, so it must be `content/fr` / `content/en` (not just `fr` / `en`);
  with the old-style `fr` / `en` values Hugo silently finds no content files.
- `layouts/partials/header.html` renders the main nav from the `main` menu
  (per-language `menu.main` entries in the page front matter) and a language
  switcher from `.AllTranslations`.
- `layouts/baseof.html` emits per-page `<link rel="alternate" hreflang>`
  alternates plus `x-default` (the default-language home), and sets
  `<html lang>` from the page's language locale.
- Translations are linked by identical path/basename under each language
  directory (Hugo's "translation by directory" scheme). To add a page in EN,
  create `content/en/<same-path>/` so Hugo links it automatically; the
  switcher picks it up with no template changes.
- The GitHub Pages deploy step (`scripts/pages-prefix.sh`) rewrites the built
  root-absolute URLs to the `/minutepapillons-org/` subpath, which also
  correctly prefixes `/en/...` links and the hreflang alternates.

## Layout

- `hugo.toml`, `content/`, `layouts/`, `static/` — Hugo source
- `public/` — built site (served as-is; `hugo build` regenerates it here)
- `build_hugo.py` — original converter from the WordPress mirror (provenance).
  It expects the WP mirror checkout next to it and outputs to `./hugo/`; the
  mirror is archived in `../minutepapillons-wp-mirror-*.tar.gz`. Do not run it
  without the mirror extracted.

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
