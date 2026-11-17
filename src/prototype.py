"""Builds docs/prototype.html: a clickable mock of the PDP 'fit badge' on real products and real review lines.
Run after analysis.py:  python src/prototype.py
"""
import html
import json
import re
from pathlib import Path

import pandas as pd

from analysis import THEMES, _pattern, tag

ROOT = Path(__file__).resolve().parents[1]
badges = pd.read_csv(ROOT / "results" / "fit_badges_all_products.csv", index_col=0)
d = pd.read_csv(ROOT / "data" / "womens_clothing_reviews.csv")
d = d[d["Review Text"].notna()].copy()
d = d.join(tag(d["Title"].fillna("") + ". " + d["Review Text"]))

# pick 2 'runs small', 2 'runs large', 1 mixed with the most fit reviews, in different classes
picks = []
for b, k in [("runs small", 2), ("runs large", 2), ("true to size / mixed", 1)]:
    sub = badges[badges.badge == b].sort_values("n", ascending=False)
    picks += list(sub.drop_duplicates("cls").head(k).index)

pat = {k: re.compile(_pattern(k, v)) for k, v in THEMES.items() if k in ("fit_small", "fit_large")}


def snippet(text, key):
    t = text.lower()
    m = pat[key].search(t)
    if not m:
        return None
    a = max(0, t.rfind(".", 0, m.start()) + 1)
    e = t.find(".", m.end())
    s = text[a:(e + 1 if e > 0 else len(text))].strip()
    return s if len(s) <= 160 else s[:160].rsplit(" ", 1)[0] + "…"


cards = []
for cid in picks:
    row = badges.loc[cid]
    rv = d[d["Clothing ID"] == cid]
    keys = {"runs small": ["fit_small"] * 2, "runs large": ["fit_large"] * 2}.get(row.badge, ["fit_small", "fit_large"])
    quotes = []
    for key in dict.fromkeys(keys):
        side = rv[rv[key] & ~(rv.fit_small & rv.fit_large)]
        got = [q for q in (snippet(x, key) for x in side["Review Text"]) if q]
        quotes += got[:keys.count(key)]
    if row.badge == "runs small":
        head, advice, pct = "Runs small", "Most shoppers who mentioned fit suggest ordering one size up.", row.share_small
    elif row.badge == "runs large":
        head, advice, pct = "Runs large", "Most shoppers who mentioned fit suggest ordering one size down.", 1 - row.share_small
    else:
        head, advice, pct = "True to size", "Fit comments are split, so stick to your usual size.", max(row.share_small, 1 - row.share_small)
    cards.append({"id": int(cid), "cls": row.cls, "rating": round(float(row.rating), 1), "reviews": int(row.reviews),
                  "head": head, "advice": advice, "pct": int(round(100 * pct)), "n": int(row.n), "quotes": quotes,
                  "badge": row.badge})

items = []
for c in cards:
    qs = "".join(f'<li>&ldquo;{html.escape(q)}&rdquo;</li>' for q in c["quotes"])
    meter = "" if c["badge"].startswith("true") else (
        f'<div class="meter"><span>Small</span><div class="bar"><i style="left:{(100 - c["pct"]) if c["badge"] == "runs small" else c["pct"]}%"></i></div><span>Large</span></div>')
    items.append(f'''<article class="pdp">
 <div class="img">{html.escape(c["cls"])}<small>Product #{c["id"]}</small></div>
 <div class="info"><h3>{html.escape(c["cls"])} &middot; product {c["id"]}</h3>
  <p class="muted">&#9733; {c["rating"]} &middot; {c["reviews"]} reviews</p>
  <div class="sizes">{"".join(f"<b>{s}</b>" for s in ["XS", "S", "M", "L", "XL"])}</div>
  <div class="badge {c["badge"].split()[1] if not c["badge"].startswith("true") else "tts"}">
   <div class="bh">{c["head"]} <span>{c["pct"]}% of {c["n"]} shoppers who mentioned fit</span></div>
   {meter}<p>{c["advice"]}</p>
   <details><summary>What shoppers said</summary><ul>{qs}</ul></details></div>
  <p class="why muted">Shown only when &ge;5 shoppers mentioned fit and &ge;65% agree. In a held-out test this rule agreed with later shoppers 87% of the time.</p>
 </div></article>''')

page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fit Badge Prototype</title><style>
:root{{--bg:#f6f5f2;--card:#fff;--ink:#222;--mut:#6b7280;--pink:#ff3f6c;--small:#2563eb;--large:#d97706;--tts:#15803d}}
body{{margin:0;background:var(--bg);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink)}}
header{{padding:20px 16px;max-width:980px;margin:auto}}h1{{font-size:22px;margin:0 0 4px}}
main{{max-width:980px;margin:auto;padding:0 16px 40px;display:grid;gap:16px}}
.pdp{{background:var(--card);border-radius:12px;display:grid;grid-template-columns:200px 1fr;overflow:hidden;box-shadow:0 1px 3px #0001}}
.img{{background:linear-gradient(135deg,#fde2e8,#e0e7ff);display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:600;color:#555;min-height:220px}}
.img small{{font-weight:400}}.info{{padding:16px}}h3{{margin:0}}.muted{{color:var(--mut);margin:4px 0}}
.sizes b{{display:inline-block;border:1px solid #d1d5db;border-radius:20px;padding:4px 12px;margin:8px 6px 8px 0;font-weight:500}}
.badge{{border-left:4px solid;border-radius:8px;padding:10px 12px;background:#fafafa}}.badge.runs{{}}
.badge.small{{border-color:var(--small)}}.badge.large{{border-color:var(--large)}}.badge.tts{{border-color:var(--tts)}}
.badge p{{margin:6px 0}}.bh{{font-weight:700}}.bh span{{font-weight:400;color:var(--mut);font-size:13px;margin-left:6px}}
.meter{{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--mut);margin-top:6px}}
.bar{{flex:1;height:6px;background:linear-gradient(90deg,var(--small),#e5e7eb,var(--large));border-radius:3px;position:relative}}
.bar i{{position:absolute;top:-4px;width:14px;height:14px;border-radius:50%;background:#111;transform:translateX(-50%)}}
details{{font-size:13px}}summary{{cursor:pointer;color:var(--pink)}}.why{{font-size:12px}}
@media(max-width:640px){{.pdp{{grid-template-columns:1fr}}.img{{min-height:100px}}}}
</style></head><body><header><h1>Fit badge: product page prototype</h1>
<p class="muted">Built from real customer reviews (public women's fashion e-commerce dataset). The product names and photos are not in the data, so they are replaced by the category and product number. Blue = runs small, amber = runs large, green = true to size.</p></header>
<main>{"".join(items)}</main></body></html>'''
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "prototype.html").write_text(page)
(ROOT / "results" / "prototype_cards.json").write_text(json.dumps(cards, indent=1))
print("saved docs/prototype.html with", len(cards), "products")
