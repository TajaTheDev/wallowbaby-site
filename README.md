# wallowbaby.com

Static site for **Wallow Baby Weaner Serum** and the free weaning recipes the bottle's QR code points to.
Hand-written HTML/CSS/JS, no framework, hosted free on Cloudflare Pages. Built the same way as the Vagina Guide site.

```
public/                  <- the live website (deploy this folder)
  index.html             home
  how-to-use/ ingredients/ safety/ faq/ contact/
  recipes/               QR code landing page + one folder per recipe (GENERATED)
  starter-guide/ thanks/ Kit opt-in for the Weaning Recipe Starter Guide
  privacy/ terms/ disclaimer/ 404.html
  assets/css/site.css    all styles
  assets/js/site.js      CONFIG block at the top: Kit form ID, Amazon link, email
  assets/fonts/          self-hosted Fredoka + Nunito (woff2)
  assets/img/            bottle, social share images, recipe photos
  _headers _redirects    Cloudflare caching/security headers and short links
  sitemap.xml robots.txt llms.txt site.webmanifest favicons
content/recipes/*.json   one file per recipe (the source of truth)
tools/recipes.py         recipe generator (Python standard library only)
tools/partials.py        shared head/header/footer used by the generator
```

## Deploy (Cloudflare Pages, free)

**Option A: connect GitHub (auto-deploys on every push)**
1. Cloudflare dashboard -> Workers & Pages -> Create -> Pages -> Connect to Git -> pick `TajaTheDev/wallowbaby-site`.
2. Framework preset: **None**. Build command: *leave empty*. Build output directory: **`public`**.
3. Save and Deploy.
4. Project -> Custom domains -> add `wallowbaby.com`, then `www.wallowbaby.com` (and add a redirect from www to the root domain).
5. Optional: project -> Metrics -> enable Web Analytics (free, no cookie banner needed).

**Option B: drag and drop (same as the Vagina Guide site)**
Workers & Pages -> Create -> Pages -> Upload assets -> project name `wallowbaby` -> drag in the **`public`** folder -> Deploy. To update: Create new deployment -> drag `public` in again.

**Before any QR-coded bottle ships:** `https://wallowbaby.com/recipes/` must be live. Never rename or remove `/recipes/`.

## The one file you edit: `public/assets/js/site.js` (top section)
- `forms.starter`: the number from your Kit form embed code for the Starter Guide. Empty = signup shows "almost ready".
- `amazon.attribution`: paste the query string from your Amazon Attribution tag (for Brand Referral Bonus). Empty = plain listing link.
- `email`: contact address used on every `data-email` link.

## Add a recipe (PowerShell)

```powershell
cd wallowbaby-site
py tools\recipes.py new "Sweet potato and lentil mash" --age 8   # ages: 6, 8, 10, 12
notepad content\recipes\sweet-potato-and-lentil-mash.json         # fill it in
py tools\recipes.py build                                          # writes the page, hub, sitemap, llms.txt
git add -A; git commit -m "Add sweet potato and lentil mash"; git push
```

`build` runs a **safety lint** first and refuses to build if a recipe for under 12 months contains honey, lists a high-risk choking food (whole nuts, popcorn, whole grapes, hard candy), or contains a top-9 allergen (milk, egg, peanut, tree nuts, wheat, soy, fish, shellfish, sesame) that isn't declared under `allergens`. It warns on juice, salt and added sugar under 12 months, and on grapes or nut butters that aren't described as cut or thinned. Run `py tools\recipes.py check` anytime.

**Recipe photos:** each recipe shows a striped placeholder with stock search words and Pexels/Unsplash links until you add the photo. Save it as `public/assets/img/recipes/<slug>.webp` (4:3, about 1200x900), run `build`, and it appears on the card, the page and in Google's recipe data.

## Placeholders still to swap (search the files for `PLACEHOLDER` and `[Photo`)
- **Directions** (`how-to-use/`, `safety/`, FAQ "Is it safe for my baby?"): pending the pediatric + regulatory review of the label. These must match the printed label word for word.
- **Ingredients:** confirm the tincture's extraction liquid and strength with the manufacturer. If it contains alcohol, list it.
- **FAQ:** how many applications a bottle gives.
- **Photos:** home page (2), recipe photos, Starter Guide cover (`assets/img/starter-guide-cover.webp`).
- **Kit:** create the Starter Guide form + delivery email, then paste its ID into `site.js`.

## Short links (`public/_redirects`)
`/buy` and `/amazon` -> Amazon listing · `/qr` -> recipes · `/guide`, `/free` -> Starter Guide · `/directions` -> How to use · `/warnings` -> Safety.
