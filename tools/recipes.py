#!/usr/bin/env python3
"""Wallow Baby recipe generator.

Recipes live as JSON files in content/recipes/. This script turns them into
static pages, the way the Vagina Guide blog posts are generated.

  python tools/recipes.py new "Sweet potato and lentil mash" --age 8
  python tools/recipes.py check        # safety + field lint (runs inside build too)
  python tools/recipes.py build        # writes public/recipes/**, sitemap.xml, llms.txt

Standard library only. Works on Windows: use `py tools\\recipes.py build`.
"""
import argparse, datetime as dt, json, re, sys, unicodedata, urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from partials import PUBLIC, ROOT, SITE, BRAND, esc, page, breadcrumbs  # noqa: E402

CONTENT = ROOT / "content" / "recipes"
OUT = PUBLIC / "recipes"
IMG_DIR = PUBLIC / "assets" / "img" / "recipes"

AGES = {
    6: ("6 months+", "Smooth & mashed", "First tastes: smooth purees, thin mashes and soft foods baby can gum. Thin with breast milk or formula as needed."),
    8: ("8 months+", "Lumpy & soft finger foods", "Thicker, lumpier mashes and soft finger foods that squash easily between your thumb and finger."),
    10: ("10 months+", "Soft bite-size pieces", "Soft, small, chopped pieces baby can pick up with a pincer grasp. Still soft enough to squash."),
    12: ("12 months+", "Family meals, made safe", "Most family foods work now, chopped small and soft. Round and hard foods still need cutting."),
}

SOURCES = [
    ("CDC: Choking hazards", "https://www.cdc.gov/infant-toddler-nutrition/foods-and-drinks/choking-hazards.html"),
    ("CDC: Foods and drinks to avoid or limit (honey before 12 months)", "https://www.cdc.gov/infant-toddler-nutrition/foods-and-drinks/foods-and-drinks-to-avoid-or-limit.html"),
    ("CDC: When, what, and how to introduce solid foods", "https://www.cdc.gov/infant-toddler-nutrition/foods-and-drinks/when-what-and-how-to-introduce-solid-foods.html"),
    ("AAP / HealthyChildren.org: When to introduce egg, peanut butter and other common allergens",
     "https://www.healthychildren.org/English/healthy-living/nutrition/Pages/when-to-introduce-egg-peanut-butter-and-other-common-food-allergens-to-your-baby-food-allergy-prevention-tips.aspx"),
]

# Top 9 US allergens -> words that signal them in an ingredient line
ALLERGEN_WORDS = {
    "Milk": r"(?<!breast )(?<!coconut )\b(milk|yogurt|yoghurt|cheese|cream|ricotta|cottage|kefir|ghee|parmesan|mozzarella|cheddar)\b|(?<!peanut )(?<!almond )(?<!nut )(?<!seed )\bbutter\b",
    "Egg": r"\begg",
    "Peanut": r"\bpeanut",
    "Tree nuts": r"\b(almond|cashew|walnut|pecan|hazelnut|pistachio|macadamia|brazil nut)",
    "Wheat": r"\b(wheat|flour|pasta|bread|couscous|semolina|noodle|macaroni|tortilla)",
    "Soy": r"\b(soy|tofu|edamame|tempeh|miso)\b",
    "Fish": r"\b(fish|salmon|cod|tuna|trout|sardine|haddock|tilapia|pollock)\b",
    "Shellfish": r"\b(shrimp|prawn|crab|lobster|scallop|clam|mussel|oyster)",
    "Sesame": r"\b(sesame|tahini)\b",
}
# word -> (min age it's acceptable, message). Errors block the build.
HARD_STOPS = [
    (r"\bhoney\b", 12, "honey before 12 months (infant botulism risk)"),
    (r"\b(whole nuts?|whole peanuts?|popcorn|hard candy|whole grapes?)\b", 48, "a high-risk choking food"),
]
WARNINGS = [
    (r"\b(?<!lemon )(?<!lime )juice\b", 12, "juice is not recommended before 12 months (CDC)"),
    (r"(?<!no-)\b(salt|soy sauce|stock cube|bouillon)\b", 12, "added salt: keep it out before 12 months"),
    (r"\b(sugar|syrup|agave|sweetened)\b", 24, "added sugars are not recommended for babies and toddlers"),
    (r"\bgrapes?\b", 48, "grapes: say 'quartered lengthwise'"),
    (r"\bcherry tomato", 48, "cherry tomatoes: say 'quartered'"),
    (r"\b(peanut butter|almond butter|nut butter)\b", 48, "nut butter: thin it out, never a thick glob or spoonful"),
]

REQUIRED = ["title", "age", "summary", "prep_min", "cook_min", "yield", "texture", "ingredients", "steps", "choking", "allergens", "storage", "photo"]


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def load():
    recipes = []
    for f in sorted(CONTENT.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        r.setdefault("slug", f.stem)
        r["_file"] = f
        recipes.append(r)
    return recipes


def lint(recipes):
    errors, warns = [], []
    slugs = set()
    for r in recipes:
        name = r["_file"].name
        for k in REQUIRED:
            if k not in r or r[k] in ("", None, []) and k not in ("allergens",):
                errors.append(f"{name}: missing '{k}'")
        if r.get("age") not in AGES:
            errors.append(f"{name}: age must be one of {sorted(AGES)}")
            continue
        if r["slug"] in slugs:
            errors.append(f"{name}: duplicate slug {r['slug']}")
        slugs.add(r["slug"])
        text = " ".join(r.get("ingredients", []) + r.get("steps", [])).lower()
        # ignore safe phrasing like "no salt needed", "no added sugar or salt", "no-salt-added"
        text = re.sub(r"\bno(-| )(added )?(sugar|salt)( or (salt|sugar))?(-added)?\b", " ", text)
        for pat, min_age, msg in HARD_STOPS:
            if re.search(pat, text) and r["age"] < min_age:
                errors.append(f"{name}: {msg}")
        for pat, min_age, msg in WARNINGS:
            if "nut butter" in msg and re.search(r"\bthin", text):
                continue  # recipe already tells parents to thin it
            if re.search(pat, text) and r["age"] < min_age:
                warns.append(f"{name}: {msg}")
        declared = {a["name"].split(" (")[0] for a in r.get("allergens", [])}
        ing = " ".join(r.get("ingredients", [])).lower()
        for allergen, pat in ALLERGEN_WORDS.items():
            if re.search(pat, ing) and allergen not in declared:
                errors.append(f"{name}: ingredients look like they contain {allergen}; add it to 'allergens' (or reword if not)")
        if not r.get("choking"):
            errors.append(f"{name}: add at least one choking note")
    return errors, warns


def iso_min(m):
    return f"PT{int(m)}M"


def photo_html(r, cls=""):
    p = r["photo"]
    f = p.get("file", "")
    if f and (IMG_DIR / f).exists():
        return f'<img class="{cls}" src="/assets/img/recipes/{esc(f)}" width="1200" height="900" alt="{esc(p.get("alt", r["title"]))}">'
    q = urllib.parse.quote(p.get("search", r["title"]))
    return (f'<div class="placeholder {cls}"><b>Photo coming soon</b><span>Stock search words:</span>'
            f'<code>{esc(p.get("search", ""))}</code>'
            f'<span class="small"><a href="https://www.pexels.com/search/{q}/" rel="noopener" target="_blank">Pexels</a> · '
            f'<a href="https://unsplash.com/s/photos/{q}" rel="noopener" target="_blank">Unsplash</a></span>'
            f'<span class="small">Save as <code>assets/img/recipes/{esc(r["slug"])}.webp</code></span></div>')


def card(r):
    label = AGES[r["age"]][0]
    tags = f'<span>{label}</span><span>{int(r["prep_min"]) + int(r["cook_min"])} min</span>'
    for a in r["allergens"]:
        tags += f'<span class="allergen">{esc(a["name"].split(" (")[0])}</span>'
    img = photo_html(r) if (r["photo"].get("file") and (IMG_DIR / r["photo"]["file"]).exists()) else \
        f'<span>📷 {esc(r["photo"].get("search", ""))}</span>'
    return f"""<a class="rcard" href="/recipes/{r['slug']}/">
  <div class="rcard__img">{img}</div>
  <div class="rcard__body"><h3>{esc(r['title'])}</h3><p class="small">{esc(r['summary'])}</p><div class="rmeta">{tags}</div></div>
</a>"""


OPTIN = """<aside class="optin bg-sun-soft">
  <img src="/assets/img/starter-guide-cover.webp" width="680" height="880" loading="lazy" alt="Weaning Recipe Starter Guide cover" style="border:3px solid var(--ink);border-radius:14px;transform:rotate(-3deg);background:#fff">
  <div class="stack" style="gap:12px">
    <p class="eyebrow">Free download</p>
    <h2 style="font-size:clamp(28px,3.4vw,38px)">The Weaning Recipe Starter Guide</h2>
    <p>Printable first recipes for every stage, a texture-by-age chart, and an allergen tracker. Free, straight to your inbox.</p>
    <form class="signup" data-kit="starter" data-redirect="/thanks/">
      <label class="big" for="{fid}">Where should we send it?</label>
      <div class="signup__row"><input id="{fid}" type="email" name="email_address" placeholder="Your email" autocomplete="email" required><button class="btn btn--red" type="submit">Send my guide</button></div>
      <div class="hp" aria-hidden="true"><input type="text" name="website" tabindex="-1" autocomplete="off"></div>
      <p class="msg" role="status" aria-live="polite"></p>
      <small>No spam. Unsubscribe any time. <a href="/privacy/">Privacy</a></small>
    </form>
  </div>
</aside>"""


def sources_html():
    return "<ol class=\"sources\">" + "".join(f'<li><a href="{u}" rel="noopener" target="_blank">{esc(n)}</a></li>' for n, u in SOURCES) + "</ol>"


def recipe_page(r, siblings):
    label, stage, _ = AGES[r["age"]]
    path = f"/recipes/{r['slug']}/"
    crumbs, crumb_ld = breadcrumbs([("Home", "/"), ("Recipes", "/recipes/"), (r["title"], path)])
    total = int(r["prep_min"]) + int(r["cook_min"])
    ing = "".join(f"<li>{esc(i)}</li>" for i in r["ingredients"])
    steps = "".join(f"<li>{esc(s)}</li>" for s in r["steps"])
    choke = "".join(f"<li>{esc(c)}</li>" for c in r["choking"])
    if r["allergens"]:
        allergy = "<ul>" + "".join(f"<li><b>{esc(a['name'])}:</b> {esc(a['note'])}</li>" for a in r["allergens"]) + "</ul>"
        allergy += ("<p class=\"small\" style=\"margin-top:8px\">New allergen? Offer it at home, earlier in the day, one new allergen at a time, then watch your baby for 2 hours. "
                    "Hives, vomiting, swelling of the face or lips, or trouble breathing: call 911.</p>")
    else:
        allergy = "<p>None of the top 9 allergens. A gentle pick for days you're not introducing anything new.</p>"
    tips = ""
    if r.get("tips"):
        tips = "<h2>Tips</h2><ul>" + "".join(f"<li>{esc(t)}</li>" for t in r["tips"]) + "</ul>"
    nohoney = "" if r["age"] >= 12 else '<div class="nohoney"><b>No honey</b><span>before 12 months, not even baked in or on a pacifier. It can cause infant botulism.</span></div>'
    milk_note = "" if r["age"] >= 12 else ("<p class=\"small\" style=\"margin-top:16px\"><b>Still under 12 months?</b> Breast milk or infant formula is still your baby's main food. "
                                          "Solids add to milk, they don't replace it. Weaning from the breast before 12 months? Ask your pediatrician which infant formula to use.</p>")
    more = [s for s in siblings if s["slug"] != r["slug"]][:3]
    more_html = ""
    if more:
        more_html = f'<section class="section bg-peri-soft noprint"><div class="wrap stack" style="gap:26px"><h2>More {label} recipes</h2><div class="grid3">' + "".join(card(s) for s in more) + "</div></div></section>"

    ld = [{
        "@type": "Recipe",
        "@id": f"{SITE}{path}#recipe",
        "name": r["title"],
        "description": r["summary"],
        "url": f"{SITE}{path}",
        "author": {"@id": f"{SITE}/#org"},
        "publisher": {"@id": f"{SITE}/#org"},
        "datePublished": r.get("date", ""),
        "prepTime": iso_min(r["prep_min"]),
        "cookTime": iso_min(r["cook_min"]),
        "totalTime": iso_min(total),
        "recipeYield": r["yield"],
        "recipeCategory": "Baby food",
        "keywords": ", ".join(r.get("tags", []) + [f"baby food {label}", "weaning recipe"]),
        "recipeIngredient": r["ingredients"],
        "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in r["steps"]],
        "inLanguage": "en-US",
    }, crumb_ld]
    if r["photo"].get("file") and (IMG_DIR / r["photo"]["file"]).exists():
        ld[0]["image"] = f"{SITE}/assets/img/recipes/{r['photo']['file']}"

    body = f"""
<article class="recipe">
<section class="page-hero"><div class="wrap recipe-hero">
  <div class="stack" style="gap:16px">
    {crumbs}
    <span class="age-badge" style="align-self:flex-start">{label} · {stage}</span>
    <h1>{esc(r['title'])}</h1>
    <p class="lede">{esc(r['summary'])}</p>
    <div class="facts"><div><b>Prep</b>{r['prep_min']} min</div><div><b>Cook</b>{r['cook_min']} min</div><div><b>Makes</b>{esc(r['yield'])}</div></div>
  </div>
  <div>{photo_html(r)}</div>
</div></section>
<section class="section" style="padding-top:48px"><div class="wrap stack" style="gap:28px">
  {nohoney}
  <div class="recipe-grid">
    <aside class="ingredients"><h2 style="font-size:30px">Ingredients</h2><ul>{ing}</ul>
      <button class="btn btn--ghost noprint" type="button" data-print style="margin-top:18px;width:100%">Print recipe</button></aside>
    <div class="prose">
      <h2 style="margin-top:0">Method</h2>
      <ol class="steps">{steps}</ol>
      <div class="safety">
        <div class="texture"><h3>Texture for {label}</h3><p>{esc(r['texture'])}</p></div>
        <div class="choke"><h3>Choking check</h3><ul>{choke}</ul><p class="small" style="margin-top:8px">Always seat baby upright and stay with them while they eat.</p></div>
        <div class="allergy"><h3>Allergens</h3>{allergy}</div>
      </div>
      <h2>Storage</h2><p>{esc(r['storage'])}</p>
      {tips}
      {milk_note}
      <div class="noprint" style="margin-top:32px">{OPTIN.replace('{fid}', 'email-' + r['slug'])}</div>
      <h2>Sources</h2>{sources_html()}
      <p class="disclaimer">General information, not medical advice. Every baby is different: check with your pediatrician before starting solids or new allergens, especially if your baby has eczema, a known allergy, or was born early.</p>
    </div>
  </div>
</div></section>
</article>
{more_html}"""
    title = f"{r['title']} ({label} baby food recipe) | {BRAND}"
    return page(title[:70] if len(title) > 70 else title, r["summary"], path, body, active="/recipes/", og="recipes", og_type="article", jsonld=ld)


def hub_page(recipes):
    by_age = {a: [r for r in recipes if r["age"] == a] for a in AGES}
    chips = "".join(f'<a class="chip" href="#age-{a}">{AGES[a][0]}</a>' for a in AGES)
    sections = ""
    for a, (label, stage, blurb) in AGES.items():
        items = by_age[a]
        grid = f'<div class="grid4">{"".join(card(r) for r in items)}</div>' if items else '<p class="empty">New recipes for this stage are on the way.</p>'
        bg = "bg-white" if a in (8, 12) else ""
        sections += f"""<section class="section {bg}" style="padding:64px 0"><div class="wrap">
  <div class="age-head" id="age-{a}"><div class="stack" style="gap:10px"><span class="age-badge" style="align-self:flex-start">{label}</span><h2>{stage}</h2></div><p style="max-width:520px">{blurb}</p></div>
  {grid}
</div></section>"""
    crumbs, crumb_ld = breadcrumbs([("Home", "/"), ("Recipes", "/recipes/")])
    item_list = {"@type": "ItemList", "name": "Weaning recipes by age", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "url": f"{SITE}/recipes/{r['slug']}/", "name": r["title"]}
        for i, r in enumerate(sorted(recipes, key=lambda x: (x["age"], x["title"])))]}
    body = f"""
<section class="page-hero"><div class="wrap stack" style="gap:14px">
  {crumbs}
  <p class="eyebrow">Scanned your bottle? Welcome 💛</p>
  <h1 class="outline">Weaning recipes,<br>sorted by age</h1>
  <p class="lede">Simple first foods for 6, 8, 10 and 12+ months, with the right texture for each stage, choking checks and allergen notes on every recipe.</p>
  <div class="chips" style="margin-top:6px">{chips}<a class="chip" href="#safety">Safety basics</a></div>
</div></section>

<section class="section" style="padding:56px 0"><div class="wrap">{OPTIN.replace('{fid}', 'email-hub')}</div></section>

<section class="section bg-ink" id="safety" style="scroll-margin-top:90px"><div class="wrap stack" style="gap:30px">
  <div class="stack" style="gap:10px"><p class="eyebrow" style="color:var(--sun)">Before you start</p><h2 style="color:var(--cream)">5 safety basics for every recipe</h2></div>
  <div class="grid3">
    <div class="card bg-cream" style="color:var(--ink)"><span class="num">1</span><h3>Milk first until 12 months</h3><p>Breast milk or infant formula stays your baby's main food until 12 months. Solids add to it. Weaning from the breast early? Ask your pediatrician which formula to use. No cow's milk as a drink and no juice before 12 months.</p></div>
    <div class="card bg-sun" style="color:var(--ink)"><span class="num">2</span><h3>No honey before 12 months</h3><p>Not in food, not baked in, not on a pacifier. Honey can carry the spores that cause infant botulism.</p></div>
    <div class="card bg-peri" style="color:var(--ink)"><span class="num">3</span><h3>Match the texture to the stage</h3><p>Smooth at 6 months, lumpy and soft at 8, small soft pieces at 10, chopped family food at 12+. If it doesn't squash between your fingers, it's not ready yet.</p></div>
    <div class="card bg-cream" style="color:var(--ink)"><span class="num">4</span><h3>Know the choking hazards</h3><p>Skip whole nuts, popcorn, hard raw veggies, whole corn kernels and hard candy. Quarter grapes and cherry tomatoes lengthwise. Thin nut butters, never a spoonful. Baby sits upright, and you stay close.</p></div>
    <div class="card bg-sun" style="color:var(--ink)"><span class="num">5</span><h3>Introduce allergens early, one at a time</h3><p>The AAP says there's no benefit to delaying allergens like egg, peanut, dairy, fish and sesame. Offer one new allergen at a time, at home, earlier in the day. Severe eczema or egg allergy? Talk to your pediatrician before peanut.</p></div>
    <div class="card bg-red" style="color:#fff"><span class="num" style="background:#fff;color:var(--ink)">!</span><h3>Gagging vs choking</h3><p>Gagging is noisy and normal while babies learn. Choking is silent: no crying, coughing or breathing. Take an infant CPR class before starting solids.</p></div>
  </div>
</div></section>

<nav class="age-nav noprint" aria-label="Jump to age"><div class="wrap chips">{chips}</div></nav>
{sections}

<section class="section bg-peri-soft"><div class="wrap prose">
  <h2 style="margin-top:0">Sources</h2>{sources_html()}
  <p class="disclaimer">These recipes are general information, not medical advice. Talk to your pediatrician before starting solids or new allergens, especially if your baby was born early, has eczema or a known allergy, or has trouble swallowing.</p>
</div></section>"""
    return page("Weaning Recipes by Age: 6, 8, 10 & 12+ Months | Wallow Baby",
                "Free baby food recipes for weaning, sorted by age: safe textures, choking checks, no honey under 12 months, and allergen notes on every recipe.",
                "/recipes/", body, active="/recipes/", og="recipes", jsonld=[item_list, crumb_ld])


STATIC_PAGES = [
    ("/", "1.0"), ("/recipes/", "0.9"), ("/starter-guide/", "0.8"), ("/how-to-use/", "0.8"), ("/ingredients/", "0.7"),
    ("/safety/", "0.7"), ("/faq/", "0.7"), ("/contact/", "0.5"), ("/privacy/", "0.3"), ("/terms/", "0.3"), ("/disclaimer/", "0.3"),
]


def write_sitemap(recipes):
    today = dt.date.today().isoformat()
    rows = [f"  <url><loc>{SITE}{p}</loc><lastmod>{today}</lastmod><priority>{pr}</priority></url>" for p, pr in STATIC_PAGES]
    rows += [f"  <url><loc>{SITE}/recipes/{r['slug']}/</loc><lastmod>{r.get('date', today)}</lastmod><priority>0.7</priority></url>" for r in recipes]
    (PUBLIC / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n", encoding="utf-8")


def write_llms(recipes):
    p = PUBLIC / "llms.txt"
    text = p.read_text(encoding="utf-8")
    block = "\n".join(f"- [{r['title']}]({SITE}/recipes/{r['slug']}/): {AGES[r['age']][0]}. {r['summary']}"
                      for r in sorted(recipes, key=lambda x: (x["age"], x["title"])))
    new = re.sub(r"(<!-- recipes:start -->\n).*?(<!-- recipes:end -->)", lambda m: m.group(1) + block + "\n" + m.group(2), text, flags=re.S)
    p.write_text(new, encoding="utf-8")


def build():
    recipes = load()
    errors, warns = lint(recipes)
    for w in warns:
        print("  warning:", w)
    if errors:
        for e in errors:
            print("  ERROR:", e)
        sys.exit("Build stopped. Fix the errors above.")
    OUT.mkdir(parents=True, exist_ok=True)
    live = set()
    for r in recipes:
        sib = sorted([s for s in recipes if s["age"] == r["age"]], key=lambda s: s["title"])
        d = OUT / r["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(recipe_page(r, sib), encoding="utf-8")
        live.add(r["slug"])
    # remove pages whose JSON was deleted
    for d in OUT.iterdir():
        if d.is_dir() and d.name not in live and (d / "index.html").exists():
            (d / "index.html").unlink(); d.rmdir(); print("  removed", d.name)
    (OUT / "index.html").write_text(hub_page(recipes), encoding="utf-8")
    write_sitemap(recipes)
    write_llms(recipes)
    print(f"Built {len(recipes)} recipes + hub, sitemap.xml, llms.txt")


TEMPLATE = {
    "title": "", "age": 6, "date": "",
    "summary": "One sentence: what it is and why babies like it.",
    "prep_min": 5, "cook_min": 10, "yield": "About 4 baby portions",
    "texture": "Describe the right texture for this age and how to adjust it.",
    "ingredients": ["1 ripe banana"],
    "steps": ["Step one."],
    "choking": ["Name the choking risk in this recipe and how to prepare it safely."],
    "allergens": [],
    "storage": "Fridge up to 2 days in a sealed container, or freeze in an ice-cube tray up to 1 month.",
    "tips": [],
    "photo": {"file": "", "alt": "", "search": "baby food puree"},
    "tags": [],
}


def new(title, age):
    slug = slugify(title)
    f = CONTENT / f"{slug}.json"
    if f.exists():
        sys.exit(f"{f} already exists")
    data = dict(TEMPLATE, title=title, age=age, date=dt.date.today().isoformat())
    data["photo"] = dict(TEMPLATE["photo"], alt=title, file=f"{slug}.webp")
    CONTENT.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created {f.relative_to(ROOT)}. Fill it in, then run: python tools/recipes.py build")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("title"); n.add_argument("--age", type=int, choices=sorted(AGES), required=True)
    sub.add_parser("build"); sub.add_parser("check")
    a = ap.parse_args()
    if a.cmd == "new":
        new(a.title, a.age)
    elif a.cmd == "check":
        e, w = lint(load())
        for x in w: print("  warning:", x)
        for x in e: print("  ERROR:", x)
        print("OK" if not e else f"{len(e)} error(s)")
        sys.exit(1 if e else 0)
    else:
        build()
