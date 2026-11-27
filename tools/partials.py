"""Shared page pieces for Wallow Baby pages (head, header, footer).

Used by tools/recipes.py to build recipe pages. The hand-written pages in
public/ contain the same header/footer; if you change the nav here, change it
in those pages too (search for 'class="nav-links"').
"""
import hashlib, html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
SITE = "https://wallowbaby.com"
BRAND = "Wallow Baby"
EMAIL = "hello@wallowbaby.com"

NAV = [
    ("/how-to-use/", "How to use"),
    ("/ingredients/", "Ingredients"),
    ("/recipes/", "Recipes"),
    ("/faq/", "FAQ"),
    ("/contact/", "Contact"),
]


def esc(s):
    return html.escape(str(s), quote=True)


def asset_version(rel):
    """Short content hash for cache-busting, like ?v=1590b6c9 on the Vagina Guide site."""
    p = PUBLIC / rel.lstrip("/")
    return hashlib.md5(p.read_bytes()).hexdigest()[:8] if p.exists() else "1"


ORG = {
    "@type": "Organization",
    "@id": f"{SITE}/#org",
    "name": BRAND,
    "legalName": "Wallow Baby LLC",
    "url": f"{SITE}/",
    "logo": f"{SITE}/icon-512x512.png",
    "email": EMAIL,
}


def head(title, description, path, og="default", og_type="website", jsonld=None, extra="", noindex=False):
    url = f"{SITE}{path}"
    img = f"{SITE}/assets/img/og/{og}.jpg"
    graph = [ORG] + (jsonld or [])
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    robots = "noindex, follow" if noindex else "index, follow, max-image-preview:large, max-snippet:-1"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{url}"><meta name="robots" content="{robots}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{img}">
<meta name="theme-color" content="#AAC5FE">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-96x96.png" type="image/png" sizes="96x96">
<link rel="icon" href="/favicon-192x192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" href="/assets/fonts/fredoka-latin-700-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/nunito-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/css/site.css?v={asset_version('assets/css/site.css')}">
<script src="/assets/js/site.js?v={asset_version('assets/js/site.js')}" defer></script>
{extra}<script type="application/ld+json">{ld}</script>
</head>"""


LOGO = '<a class="logo" href="/" aria-label="Wallow Baby home"><span>W</span><span>a</span><span>l</span><span>l</span><span>o</span><span>w</span><small>BABY</small></a>'


def header(active=""):
    links = "\n".join(
        f'      <a href="{href}"{" aria-current=page" if href == active else ""}>{label}</a>' for href, label in NAV
    )
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <nav class="wrap nav" aria-label="Main">
    {LOGO}
    <button class="menu-btn" aria-expanded="false" aria-controls="nav-links">Menu</button>
    <div class="nav-links" id="nav-links">
{links}
      <a class="btn btn--sun" data-amazon href="/buy">Buy on Amazon</a>
    </div>
  </nav>
</header>
<main id="main">
"""


def footer():
    return f"""</main>
<footer class="site-footer">
  <div class="wrap">
    <div class="foot-top">
      {LOGO}
      <div class="foot-links">
        <a href="/recipes/">Weaning recipes</a>
        <a href="/starter-guide/">Free starter guide</a>
        <a href="/safety/">Safety</a>
        <a href="/faq/">FAQ</a>
        <a data-amazon href="/buy">Amazon store</a>
        <a data-email href="mailto:{EMAIL}">{EMAIL}</a>
      </div>
    </div>
    <p class="foot-small">Wallow Baby Weaner Serum is a topical cosmetic product. It is not intended to diagnose, treat, cure or prevent any disease. Recipes and weaning information on this site are general education, not medical advice. Talk to your pediatrician about your own baby. As an Amazon seller we may earn from purchases made through links on this site.</p>
    <div class="foot-legal">
      <span>&copy; <span data-year>2026</span> Wallow Baby LLC</span>
      <a href="/privacy/">Privacy</a>
      <a href="/terms/">Terms</a>
      <a href="/disclaimer/">Disclaimer</a>
    </div>
  </div>
</footer>
</body>
</html>
"""


def breadcrumbs(items):
    """items: list of (name, path). Returns (html, jsonld)."""
    html_ = " / ".join(f'<a href="{p}">{esc(n)}</a>' for n, p in items)
    ld = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{SITE}{p}"} for i, (n, p) in enumerate(items)
        ],
    }
    return f'<nav class="crumbs" aria-label="Breadcrumb">{html_}</nav>', ld


def page(title, description, path, body, active="", **kw):
    return head(title, description, path, **kw) + "\n" + header(active) + body + "\n" + footer()
