#!/usr/bin/env python3
"""Builds the Weaning Recipe Starter Guide PDF (the Kit opt-in freebie).

  pip install reportlab segno fonttools brotli
  python tools/starter_guide.py

Output: deliverables/Wallow-Weaning-Recipe-Starter-Guide.pdf (upload this to Kit,
it is NOT published on the website) and public/assets/img/starter-guide-cover.webp
if pdftoppm is available. Recipe pages are pulled from content/recipes/*.json.
"""
import json, subprocess, shutil, sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, KeepTogether, NextPageTemplate, Flowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from fontTools.ttLib import TTFont as FTFont
import segno

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "public" / "assets" / "fonts"
OUT = ROOT / "deliverables"
CACHE = ROOT / ".font-cache"

PERI, PERI_SOFT, SUN, SUN_SOFT, RED, CREAM, INK = (HexColor(c) for c in
    ("#AAC5FE", "#DCE7FF", "#F8C000", "#FFE89A", "#F4592F", "#FFF6DE", "#1E2560"))
LOGO = ["#F4592F", "#E8508B", "#F8C000", "#3BB3E6", "#7AC043", "#F48C1F"]


def register_fonts():
    """reportlab needs TTF; the site ships woff2, so convert once into .font-cache/."""
    CACHE.mkdir(exist_ok=True)
    for name, f in [("Fredoka", "fredoka-latin-700-normal"), ("Nunito", "nunito-latin-400-normal"),
                    ("Nunito-Bold", "nunito-latin-700-normal"), ("Nunito-Black", "nunito-latin-800-normal")]:
        ttf = CACHE / f"{f}.ttf"
        if not ttf.exists():
            t = FTFont(FONTS / f"{f}.woff2"); t.flavor = None; t.save(ttf)
        pdfmetrics.registerFont(TTFont(name, str(ttf)))


register_fonts()
S = {
    "h1": ParagraphStyle("h1", fontName="Fredoka", fontSize=30, leading=33, textColor=INK, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Fredoka", fontSize=19, leading=22, textColor=INK, spaceBefore=6, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="Nunito-Black", fontSize=11.5, leading=14, textColor=INK, spaceAfter=3),
    "eb": ParagraphStyle("eb", fontName="Nunito-Black", fontSize=9, leading=11, textColor=RED, spaceAfter=4),
    "p": ParagraphStyle("p", fontName="Nunito", fontSize=10.5, leading=14.5, textColor=INK, spaceAfter=6),
    "sm": ParagraphStyle("sm", fontName="Nunito", fontSize=9, leading=12, textColor=INK),
    "li": ParagraphStyle("li", fontName="Nunito", fontSize=9.5, leading=12.5, textColor=INK, leftIndent=12, bulletIndent=2, spaceAfter=2),
    "cell": ParagraphStyle("cell", fontName="Nunito", fontSize=9.5, leading=12.5, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Nunito-Black", fontSize=9.5, leading=12.5, textColor=INK),
    "th": ParagraphStyle("th", fontName="Nunito-Black", fontSize=9.5, leading=12, textColor=CREAM),
}
P = lambda t, s="p": Paragraph(t, S[s])
bullets = lambda items, s="li": [Paragraph(i, S[s], bulletText="•") for i in items]
W, H = letter
M = 0.65 * inch


def frame_page(c, doc):
    c.saveState()
    c.setFillColor(CREAM); c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(PERI); c.rect(0, H - 0.42 * inch, W, 0.42 * inch, stroke=0, fill=1)
    x = M
    for ch, col in zip("Wallow", LOGO):
        c.setFillColor(HexColor(col)); c.setFont("Fredoka", 14); c.drawString(x, H - 0.29 * inch, ch); x += pdfmetrics.stringWidth(ch, "Fredoka", 14)
    c.setFillColor(INK); c.setFont("Nunito-Black", 8); c.drawRightString(W - M, H - 0.27 * inch, "WEANING RECIPE STARTER GUIDE")
    c.setFont("Nunito", 8); c.drawString(M, 0.4 * inch, "General information, not medical advice. Ask your pediatrician about your own baby.")
    c.drawRightString(W - M, 0.4 * inch, f"wallowbaby.com/recipes  ·  {doc.page}")
    c.restoreState()


def cover(c, doc):
    c.saveState()
    c.setFillColor(PERI); c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(SUN); c.circle(W - 1.2 * inch, H - 1.6 * inch, 3.1 * inch, stroke=0, fill=1)
    c.setFillColor(RED); c.circle(0.6 * inch, 1.0 * inch, 1.6 * inch, stroke=0, fill=1)
    c.setFillColor(CREAM); c.roundRect(M, H - 1.9 * inch, 2.9 * inch, 0.95 * inch, 0.47 * inch, stroke=0, fill=1)
    x = M + 0.28 * inch
    for ch, col in zip("Wallow", LOGO):
        c.setFillColor(HexColor(col)); c.setFont("Fredoka", 44); c.drawString(x, H - 1.62 * inch, ch); x += pdfmetrics.stringWidth(ch, "Fredoka", 44)
    c.setFillColor(RED); c.setFont("Fredoka", 12); c.drawString(x + 2, H - 1.66 * inch, "BABY")
    c.setFillColor(INK); c.setFont("Nunito-Black", 13); c.drawString(M, H - 3.0 * inch, "FREE PRINTABLE GUIDE")
    y = H - 3.85 * inch
    for line in ["Weaning", "Recipe", "Starter Guide"]:
        c.saveState()
        c.setLineWidth(3); c.setStrokeColor(INK); c.setFillColor(white)
        t = c.beginText(M, y); t.setTextRenderMode(2); t.setFont("Fredoka", 58); t.textLine(line); c.drawText(t)
        c.restoreState()
        y -= 0.85 * inch
    c.setFillColor(INK); c.setFont("Nunito-Bold", 15)
    c.drawString(M, y - 0.05 * inch, "First foods for 6, 8, 10 & 12+ months")
    items = ["Texture-by-age chart", "8 starter recipes with choking checks", "Allergen tracker for the top 9", "The “not before 12 months” list"]
    yy = y - 0.6 * inch
    for it in items:
        c.setFillColor(CREAM); c.circle(M + 0.1 * inch, yy + 4, 7, stroke=0, fill=1)
        c.setFillColor(INK); c.setFont("Nunito-Black", 9); c.drawCentredString(M + 0.1 * inch, yy + 1, "✓")
        c.setFont("Nunito-Bold", 13); c.drawString(M + 0.32 * inch, yy, it); yy -= 0.32 * inch
    c.setFont("Nunito-Black", 11); c.drawRightString(W - M, 0.6 * inch, "wallowbaby.com")
    c.restoreState()


class Box(Flowable):
    """Rounded colored box around a list of flowables."""
    def __init__(self, content, bg=white, pad=12, radius=12, border=INK, width=None):
        super().__init__(); self.content, self.bg, self.pad, self.radius, self.border, self.w0 = content, bg, pad, radius, border, width
    def wrap(self, aw, ah):
        self.w = self.w0 or aw
        self.inner = [(f, f.wrap(self.w - 2 * self.pad, ah)) for f in self.content]
        self.h = sum(h for _, (w, h) in self.inner) + sum(f.getSpaceAfter() for f in self.content) + 2 * self.pad
        return self.w, self.h
    def draw(self):
        c = self.canv; c.setFillColor(self.bg); c.setStrokeColor(self.border); c.setLineWidth(1.6)
        c.roundRect(0, 0, self.w, self.h, self.radius, stroke=1, fill=1)
        y = self.h - self.pad
        for f, (w, h) in self.inner:
            y -= h; f.drawOn(c, self.pad, y); y -= f.getSpaceAfter()


def grid(boxes, cols=2, gap=10):
    colw = (W - 2 * M - gap * (cols - 1)) / cols
    rows = [boxes[i:i + cols] for i in range(0, len(boxes), cols)]
    data = [[b for b in r] + [""] * (cols - len(r)) for r in rows]
    t = Table(data, colWidths=[colw + (gap if i < cols - 1 else 0) for i in range(cols)])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), gap), ("BOTTOMPADDING", (0, 0), (-1, -1), gap), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
    for b in boxes: b.w0 = colw
    return t


def table(rows, widths, head_bg=INK, zebra=PERI_SOFT):
    data = [[Paragraph(c, S["th"]) for c in rows[0]]] + [[Paragraph(c, S["cellb"] if j == 0 else S["cell"]) for j, c in enumerate(r)] for r in rows[1:]]
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), head_bg), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("BOX", (0, 0), (-1, -1), 1.4, INK), ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#9AA3D6")),
          ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 7)]
    for i in range(1, len(data)):
        st.append(("BACKGROUND", (0, i), (-1, i), zebra if i % 2 else white))
    t.setStyle(TableStyle(st)); return t


def recipe_block(r):
    label = {6: "6 MONTHS+", 8: "8 MONTHS+", 10: "10 MONTHS+", 12: "12 MONTHS+"}[r["age"]]
    left = [P("Ingredients", "h3")] + bullets(r["ingredients"])
    right = [P("Method", "h3")] + [Paragraph(s, S["li"], bulletText=f"{i + 1}.") for i, s in enumerate(r["steps"])]
    two = Table([[left, right]], colWidths=[(W - 2 * M) * 0.38, (W - 2 * M) * 0.62])
    two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
    allergen = "; ".join(f"<b>{a['name']}</b>: {a['note']}" for a in r["allergens"]) or "None of the top 9 allergens."
    notes = Box([P(f"<b>Texture:</b> {r['texture']}", "sm"), Spacer(1, 3),
                 P("<b>Choking check:</b> " + " ".join(r["choking"]), "sm"), Spacer(1, 3),
                 P(f"<b>Allergens:</b> {allergen}", "sm")], bg=SUN_SOFT, pad=9, radius=10)
    return KeepTogether([P(f"{label}  ·  {r['prep_min'] + r['cook_min']} MIN  ·  {r['yield'].upper()}", "eb"),
                         P(r["title"], "h2"), P(r["summary"]), two, Spacer(1, 4), notes, Spacer(1, 10)])


def build():
    recipes = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "content" / "recipes").glob("*.json")}
    picks = [("avocado-banana-mash", "red-lentil-carrot-puree"), ("spinach-omelet-strips", "beef-sweet-potato-mash"),
             ("salmon-potato-cakes", "crispy-soft-tofu-bites"), ("banana-oat-pancakes", "turkey-veggie-meatballs")]
    OUT.mkdir(exist_ok=True)
    pdf = OUT / "Wallow-Weaning-Recipe-Starter-Guide.pdf"
    doc = BaseDocTemplate(str(pdf), pagesize=letter, leftMargin=M, rightMargin=M, topMargin=0.75 * inch, bottomMargin=0.7 * inch,
                          title="Weaning Recipe Starter Guide", author="Wallow Baby LLC", subject="Baby food recipes by age")
    fr = Frame(M, 0.7 * inch, W - 2 * M, H - 1.45 * inch, id="f")
    doc.addPageTemplates([PageTemplate("cover", [Frame(0, 0, W, H)], onPage=cover), PageTemplate("body", [fr], onPage=frame_page)])
    st = [NextPageTemplate("body"), PageBreak()]

    # --- welcome + safety basics
    st += [P("WELCOME", "eb"), P("Let’s start with the basics", "h1"),
           P("As nursing winds down, mealtimes ramp up. This guide gives you a simple path through the first year of food: what texture to aim for at each stage, what to skip until 12 months, how to introduce allergens, and eight recipes to get you going. More recipes, sorted by age, live at <b>wallowbaby.com/recipes</b>."),
           Spacer(1, 8)]
    basics = [
        ("1. Milk first until 12 months", "Breast milk or infant formula stays your baby’s main food until 12 months. Solids add to it, they don’t replace it. Weaning from the breast before 12 months? Ask your pediatrician which infant formula to use.", PERI),
        ("2. No honey before 12 months", "Not in food, not baked in, not on a pacifier. Honey can carry the spores that cause infant botulism.", SUN),
        ("3. Match texture to the stage", "Smooth at 6 months, lumpy and soft at 8, small soft pieces at 10, chopped family food at 12+. If it doesn’t squash between your thumb and finger, it isn’t ready.", white),
        ("4. Know the choking hazards", "No whole nuts, popcorn, hard raw veggies, whole corn kernels or hard candy. Quarter grapes and cherry tomatoes lengthwise. Thin nut butters. Baby sits upright and you stay close.", white),
        ("5. Introduce allergens early, one at a time", "There’s no benefit to delaying allergens. Offer one new allergen at a time, at home, earlier in the day, and keep it in the diet once it’s tolerated.", SUN_SOFT),
        ("Gagging vs choking", "Gagging is noisy (coughing, sputtering) and normal while babies learn. Choking is silent: no crying, coughing or breathing. Take an infant CPR class before starting solids.", HexColor("#FFE3DA")),
    ]
    st += [grid([Box([P(t, "h3"), P(b, "sm")], bg=bg) for t, b, bg in basics])]
    st += [PageBreak()]

    # --- texture chart
    st += [P("TEXTURE BY AGE", "eb"), P("What to serve, stage by stage", "h1"),
           P("Every baby moves at their own pace. Use these as a guide, and move up when your baby handles the current texture easily. Babies who were born early may move more slowly: follow your pediatrician’s advice."),
           table([["Age", "Texture", "Try", "How to cut it"],
                  ["6 months+", "Smooth purees and thin mashes. Soft foods baby can gum.", "Avocado, sweet potato, lentils, infant oat cereal, plain yogurt, banana.", "Blend or mash until smooth. Thin with breast milk or formula."],
                  ["8 months+", "Thicker, lumpier mashes. Soft finger foods that squash easily.", "Soft omelet strips, broccoli trees, beef or lentil mash, hummus, ricotta.", "Finger-length strips baby can hold in a fist. Mash with a fork, not a blender."],
                  ["10 months+", "Soft, small, chopped pieces for the pincer grasp.", "Soft tofu, shredded chicken, small soft pasta, soft fruit, salmon cakes.", "Pea-size soft pieces, or a soft piece to bite from. Squash round foods."],
                  ["12 months+", "Most family foods, chopped small and soft.", "Meatballs, mac and cheese, quesadilla strips, fried rice, pancakes.", "Cut round foods into quarters. Keep pieces small and soft."]],
                 [0.95 * inch, 1.85 * inch, 2.05 * inch, 2.35 * inch]),
           Spacer(1, 14), P("Signs your baby is ready for solids", "h2"),
           *bullets(["Around 6 months old (not before 4 months).", "Sits up with little or no support and holds their head steady.",
                     "Opens their mouth when food comes their way and can move food to the back of the mouth to swallow.",
                     "Shows interest in what you’re eating."]),
           PageBreak()]

    # --- not before 12 months + choking prep
    st += [P("THE “NOT YET” LIST", "eb"), P("Skip these before 12 months", "h1"),
           grid([Box([P("Honey", "h3"), P("Any kind, including baked in or on a pacifier. Risk of infant botulism.", "sm")], bg=SUN),
                 Box([P("Cow’s milk as a drink", "h3"), P("Wait until 12 months. Yogurt and cheese are fine before then.", "sm")], bg=PERI),
                 Box([P("Juice", "h3"), P("Including 100% juice. Offer whole fruit instead and small sips of water from 6 months.", "sm")], bg=white),
                 Box([P("Added salt and sugar", "h3"), P("No added salt before 12 months, and no added sugars for babies and toddlers. Season the grown-ups’ portion separately.", "sm")], bg=white),
                 Box([P("Unpasteurized foods", "h3"), P("Raw milk, unpasteurized cheese, yogurt and juice. Choose pasteurized products.", "sm")], bg=white),
                 Box([P("Undercooked egg, meat and fish", "h3"), P("Cook eggs until firm and meat and fish all the way through.", "sm")], bg=white)]),
           Spacer(1, 6), P("High-risk choking foods, and how to make them safer", "h2"),
           table([["Food", "Safer way to serve"],
                  ["Grapes, cherry tomatoes, blueberries", "Quarter lengthwise or smash flat"],
                  ["Whole nuts and seeds", "Not before age 4. Use smooth nut butters, thinned, in a thin layer"],
                  ["Nut butter by the spoonful", "Thin with water and stir into food, or spread thinly on toast"],
                  ["Raw carrot, apple, celery", "Cook until soft, or grate finely"],
                  ["Hot dogs and sausages", "Not for babies. For toddlers, quarter lengthwise and chop small"],
                  ["Chunks of meat or cheese", "Shred meat finely; grate or thinly slice cheese"],
                  ["Popcorn, chips, hard candy, gum", "Skip for babies and young toddlers"]],
                 [2.6 * inch, 4.6 * inch]),
           PageBreak()]

    # --- allergen tracker
    st += [P("ALLERGEN TRACKER", "eb"), P("The top 9, one at a time", "h1"),
           P("Offer each new allergen at home, earlier in the day, when your baby is well. Start with a small amount, then watch for 2 hours. Once it’s tolerated, keep it in their diet a few times a week. If your baby has severe eczema or an egg allergy, talk to your pediatrician before introducing peanut."),
           table([["Allergen", "Easy first form", "1st try", "2nd try", "3rd try", "Notes"],
                  ["Peanut", "Smooth peanut butter thinned into oatmeal", "", "", "", ""],
                  ["Egg", "Well-cooked omelet strips", "", "", "", ""],
                  ["Milk (dairy)", "Plain whole-milk yogurt", "", "", "", ""],
                  ["Wheat", "Soft toast strips or small pasta", "", "", "", ""],
                  ["Soy", "Soft tofu", "", "", "", ""],
                  ["Sesame", "Tahini in hummus", "", "", "", ""],
                  ["Fish", "Flaked salmon, bones removed", "", "", "", ""],
                  ["Shellfish", "Finely chopped cooked shrimp", "", "", "", ""],
                  ["Tree nuts", "Thinned almond or cashew butter", "", "", "", ""]],
                 [1.0 * inch, 1.95 * inch, 0.7 * inch, 0.7 * inch, 0.7 * inch, 2.15 * inch], zebra=SUN_SOFT),
           Spacer(1, 12),
           Box([P("When to get help", "h3"),
                P("<b>Call 911</b> for trouble breathing, wheezing, swelling of the lips, face or tongue, repeated vomiting, or if your baby is pale, floppy or very sleepy. "
                  "<b>Call your pediatrician</b> for a mild rash or hives around the mouth, or any reaction you’re unsure about, and pause that food until you’ve talked.", "sm")],
               bg=HexColor("#FFE3DA")),
           PageBreak()]

    # --- recipes
    for a, b in picks:
        st += [recipe_block(recipes[a]), recipe_block(recipes[b]), PageBreak()]

    # --- closing page with QR
    qr = segno.make_qr("https://wallowbaby.com/recipes", error="q", boost_error=False)
    qrpng = CACHE / "qr.png"; qr.save(str(qrpng), scale=12, border=4)
    from reportlab.platypus import Image as RLImage
    st += [P("KEEP GOING", "eb"), P("More recipes, sorted by age", "h1"),
           P("Find every recipe, with a choking check and allergen notes on each one, at <b>wallowbaby.com/recipes</b>. Scan to open it on your phone:"),
           Spacer(1, 6), RLImage(str(qrpng), width=1.6 * inch, height=1.6 * inch, hAlign="LEFT"), Spacer(1, 16),
           P("Sources", "h2"),
           *bullets(["CDC: Choking hazards (cdc.gov/infant-toddler-nutrition/foods-and-drinks/choking-hazards.html)",
                     "CDC: Foods and drinks to avoid or limit (cdc.gov/infant-toddler-nutrition/foods-and-drinks/foods-and-drinks-to-avoid-or-limit.html)",
                     "CDC: When, what, and how to introduce solid foods (cdc.gov/infant-toddler-nutrition)",
                     "AAP / HealthyChildren.org: When to introduce egg, peanut butter and other common allergens"], "sm"),
           Spacer(1, 12),
           P("This guide is general information, not medical advice. Every baby is different. Talk to your pediatrician before starting solids or new allergens, especially if your baby was born early, has eczema or a known allergy, or has trouble swallowing. Wallow Baby Weaner Serum is a topical cosmetic product and is not intended to diagnose, treat, cure or prevent any disease. © Wallow Baby LLC.", "sm")]
    doc.build(st)
    print("PDF:", pdf.relative_to(ROOT))

    if shutil.which("pdftoppm"):
        tmp = CACHE / "cover"
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "80", "-png", str(pdf), str(tmp)], check=True)
        from PIL import Image
        png = next(CACHE.glob("cover*.png"))
        Image.open(png).save(ROOT / "public" / "assets" / "img" / "starter-guide-cover.webp", quality=85)
        png.unlink()
        print("Cover: public/assets/img/starter-guide-cover.webp")


if __name__ == "__main__":
    build()
