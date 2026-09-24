#!/usr/bin/env python3
"""Convert the minutepapillons.org WordPress static mirror into a clean Hugo site (./hugo).

All WordPress references are stripped:
  - assets remapped: wp-content/* -> assets/{uploads,plugins,themes}/*, wp-includes/* -> assets/core/*
  - no WordPress JS (navigation module, emoji, jquery, wpforms) — replaced by a small vanilla nav toggle
  - wp-/wpforms class and attribute names rewritten to neutral names in HTML + CSS
  - "WordPress" branding text replaced
"""
import os, re, shutil, sys

SRC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SRC, "hugo")

PAGES = [
    ("index.html",                         "_index",                 True),
    ("220-2/index.html",                   "220-2",                  False),
    ("louez-moi/index.html",               "louez-moi",              False),
    ("on-parle-de-votre-projet/index.html","on-parle-de-votre-projet",False),
    ("questions-frequentes/index.html",    "questions-frequentes",   False),
    ("trouver-nos-cabines/index.html",     "trouver-nos-cabines",    False),
]

ROUTE_BY_ID = {
    "219": "/questions-frequentes/",
    "220": "/220-2/",
    "221": "/louez-moi/",
    "222": "/trouver-nos-cabines/",
    "223": "/on-parle-de-votre-projet/",
}
SECTION_DIRS = set(d for d, _, _ in PAGES[1:])

ATTR_RE = re.compile(r'''(?:src|href|poster|data-lazy-src|data-lazy-srcset|content|action)\s*=\s*["\']([^"\']+)["\']''')
URL_IN_CSS_RE = re.compile(r'''url\(\s*["']?([^"')]+)["']?\s*\)''')
SRCSET_RE = re.compile(r'''srcset\s*=\s*["\']([^"\']+)["\']''')
DATA_WP_RE = re.compile(r"""\s+data-wp-[\w-]+(?:=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?""")

collected_assets = set()  # original repo-relative paths (wp-content/..., wp-includes/...)


def new_asset_path(orig: str) -> str:
    """Map an original mirror asset path to its clean location under assets/."""
    for a, b in (("wp-content/uploads/", "assets/uploads/"),
                 ("wp-content/plugins/", "assets/plugins/"),
                 ("wp-content/themes/", "assets/themes/"),
                 ("wp-includes/", "assets/core/")):
        if orig.startswith(a):
            return b + orig[len(a):]
    return "assets/" + orig


def local_path(u: str):
    """Map any mirror URL form to a repo-relative source path, or None."""
    u = u.strip()
    for prefix in ("http://localhost:8881", "http://127.0.0.1:8881"):
        if u.startswith(prefix):
            u = u[len(prefix):]
    if u.startswith("https://www.minutepapillons.org"):
        u = u[len("https://www.minutepapillons.org"):]
    u = u.split("#")[0].split("?")[0]
    u = unquote_u(u)
    if u.startswith("./"):
        u = u[2:]
    if u.startswith("../"):
        u = u[3:]
    if u.startswith("/"):
        u = u[1:]
    if u.startswith(("wp-content/", "wp-includes/", "wp-json/")):
        return u
    return None


def unquote_u(s):
    from urllib.parse import unquote
    return unquote(s)


def route_for(href: str):
    from urllib.parse import unquote
    h = unquote(href)
    m = re.match(r"index\.html\?(?:p|page_id)=(\d+)(\.html)?(.*)$", h)
    if m and m.group(1) in ROUTE_BY_ID:
        return ROUTE_BY_ID[m.group(1)] + m.group(3)
    if href == "index.html":
        return "/"
    m = re.match(r"([\w-]+)/index\.html", href)
    if m and m.group(1) in SECTION_DIRS:
        return "/" + m.group(1) + "/"
    return None


def _sub_once(s, old, new):
    i = s.find(old)
    return s[:i] + new + s[i + len(old):] if i >= 0 else s


def rewrite_html(html: str) -> str:
    def repl_attr(m):
        u = m.group(1)
        lp = local_path(u)
        if lp:
            collected_assets.add(lp)
            return _sub_once(m.group(0), u, "/" + new_asset_path(lp))
        if not u.startswith(("http://", "https://")):
            r = route_for(u)
            if r:
                return _sub_once(m.group(0), u, r)
        return m.group(0)

    html = ATTR_RE.sub(repl_attr, html)

    def repl_srcset(m):
        def one(part):
            part = part.strip()
            u = part.split(" ")[0]
            lp = local_path(u)
            if lp:
                collected_assets.add(lp)
                return "/" + new_asset_path(lp) + part[len(u):]
            return part
        return 'srcset="' + ", ".join(one(p) for p in m.group(1).split(",")) + '"'
    html = SRCSET_RE.sub(repl_srcset, html)
    html = DATA_WP_RE.sub("", html)
    return html


def scrub(s: str) -> str:
    """Remove WordPress fingerprints from HTML/CSS text."""
    s = re.sub(r"WordPress", "Minute papillons", s)
    s = re.sub(r"wordpress", "minutepapillons", s)
    s = s.replace("wpforms", "contact")
    s = s.replace("wp-", "")
    return s


def css_local(u: str, css_dir: str):
    u = u.strip().strip('"\'')
    if u.startswith(("http://", "https://", "data:", "#")):
        return None
    if u.startswith("/"):
        u = u[1:]
    if u.startswith(("wp-content/", "wp-includes/")):
        return u
    p = os.path.normpath(os.path.join(css_dir, u))
    if p.startswith(".."):
        return None
    return p


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    for d in ("content", "layouts", "layouts/partials", "static/css"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    home_html = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()

    # ---------- stylesheets linked from page heads (union across pages) ----------
    sheet_paths, seen_sheets = [], set()
    for f, _, _ in PAGES:
        h = open(os.path.join(SRC, f), encoding="utf-8").read()
        head = h[:h.index("<body")]
        for lm in re.finditer(r"<link[^>]*rel=[\"']stylesheet[\"'][^>]*>", head):
            hm = re.search(r"href=([\"'])([^\"']+)\1", lm.group(0))
            if not hm:
                continue
            import urllib.parse
            lp = local_path(hm.group(2))  # raw: local_path handles %3F vs real queries
            if lp and lp not in seen_sheets:
                seen_sheets.add(lp)
                sheet_paths.append(lp)
    collected_assets.update(seen_sheets)
    sheet_links = "\n".join(
        "<link rel='stylesheet' href='%s' media='all' />" % scrub("/" + new_asset_path(p)).replace("?", "%3F")
        for p in sheet_paths
    )

    # ---------- head inline styles (from all pages, deduped) ----------
    styles, seen = [], set()
    for f, _, _ in PAGES:
        h = open(os.path.join(SRC, f), encoding="utf-8").read()
        head = h[:h.index("<body")]
        for sm in re.finditer(r"<style[^>]*>(.*?)</style>", head, re.S):
            css = sm.group(1)
            key = css.strip()
            if key in seen:
                continue
            seen.add(key)

            def css_url(m, _css_dir=""):
                lp = local_path(m.group(1).strip())
                if lp:
                    collected_assets.add(lp)
                    return 'url("/' + new_asset_path(lp) + '")'
                return m.group(0)

            css = URL_IN_CSS_RE.sub(css_url, css)
            styles.append(css)
    head_css = scrub("\n".join(styles))
    open(os.path.join(OUT, "static/css/head-inline.css"), "w", encoding="utf-8").write(head_css)

    # ---------- header / footer partials ----------
    header = home_html[home_html.index("<header"):home_html.index("<main")]
    fstart = home_html.index("<footer")
    fend = home_html.index("</footer>") + len("</footer>")
    footer = home_html[fstart:fend]
    header = scrub(rewrite_html(header))
    footer = scrub(rewrite_html(footer))
    open(os.path.join(OUT, "layouts/partials/header.html"), "w", encoding="utf-8").write(header)
    open(os.path.join(OUT, "layouts/partials/footer.html"), "w", encoding="utf-8").write(footer)

    # ---------- templates ----------
    baseof = '''<!DOCTYPE html>
<html lang="fr-FR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{{ .Title }}</title>
__SHEET_LINKS__
<link rel='stylesheet' href='/css/head-inline.css' media='all' />
</head>
<body class="custom-logo embed-responsive theme-twentytwentyfour">
<div class="site-blocks">
{{ partial "header.html" . }}
{{ block "main" . }}{{ end }}
{{ partial "footer.html" . }}
</div>
<script>
/* minimal accessible menu toggle (replaces the previous CMS behaviour) */
(function () {
  var openBtn = document.querySelector('.block-navigation__responsive-container-open');
  var box = document.querySelector('.block-navigation__responsive-container');
  var closeBtn = document.querySelector('.block-navigation__responsive-close');
  if (!openBtn || !box) return;
  function setOpen(on) {
    box.classList.toggle('is-menu-open', on);
    openBtn.classList.toggle('is-menu-open', on);
    box.setAttribute('aria-hidden', on ? 'false' : 'true');
  }
  openBtn.addEventListener('click', function () { setOpen(true); });
  if (closeBtn) closeBtn.addEventListener('click', function () { setOpen(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
})();
</script>
</body>
</html>
'''
    baseof = baseof.replace("__SHEET_LINKS__", sheet_links)
    open(os.path.join(OUT, "layouts/baseof.html"), "w", encoding="utf-8").write(baseof)
    index_tmpl = '{{ define "main" }}{{ .Content }}{{ end }}\n'
    open(os.path.join(OUT, "layouts/index.html"), "w", encoding="utf-8").write(index_tmpl)
    open(os.path.join(OUT, "layouts/section.html"), "w", encoding="utf-8").write(index_tmpl)

    # ---------- content pages ----------
    for f, section, is_home in PAGES:
        h = open(os.path.join(SRC, f), encoding="utf-8").read()
        m = re.search(r"<main[^>]*>.*?</main>", h, re.S)
        body = scrub(rewrite_html(m.group(0)))
        import html as _html
        title = _html.unescape(re.search(r"<title>(.*?)</title>", h, re.S).group(1)).strip()
        if is_home:
            page_title = "Minute papillons"
        else:
            page_title = re.sub(r"\s*[–\-]\s*Minute papillons$", "", title)
        fm = f'---\ntitle: "{page_title}"\nmarkup: html\n---\n'
        if section == "_index":
            dest = os.path.join(OUT, "content", "_index.html")
        else:
            dest = os.path.join(OUT, "content", section, "_index.html")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8").write(fm + body + "\n")

    # ---------- copy referenced assets (remapped, scrubbed css) ----------
    queue = list(collected_assets)
    copied = set()
    while queue:
        rel = queue.pop()
        if rel in copied:
            continue
        copied.add(rel)
        src = os.path.join(SRC, rel)
        if not os.path.isfile(src):
            print("MISSING SOURCE:", rel)
            continue
        dst = os.path.join(OUT, "static", scrub(new_asset_path(rel)))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        if rel.endswith(".css"):
            css = open(src, encoding="utf-8", errors="replace").read()
            # scrub css (branding + wp- class prefixes)
            css = scrub(css)
            open(dst, "w", encoding="utf-8").write(css)
            # follow url() references (original paths, relative to the file)
            for um in URL_IN_CSS_RE.finditer(open(src, encoding="utf-8", errors="replace").read()):
                p = css_local(um.group(1), os.path.dirname(rel))
                if p and os.path.isfile(os.path.join(SRC, p)):
                    collected_assets.add(p)
                    queue.append(p)
    print("assets copied:", len(copied))

    # ---------- hugo config ----------
    open(os.path.join(OUT, "hugo.toml"), "w", encoding="utf-8").write(
        'baseURL = "/"\nlanguageCode = "fr-FR"\ndefaultContentLanguage = "fr"\ntitle = "Minute papillons"\n')
    print("done ->", OUT)


if __name__ == "__main__":
    main()
