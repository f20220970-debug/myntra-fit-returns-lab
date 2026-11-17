"""Business case for the fit badge as a live Excel model: python src/business_case.py -> fit_badge_business_case.xlsx
Blue = input, yellow = change me, black = formula. Every input has a source or is marked ASSUMPTION."""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

ROOT = Path(__file__).resolve().parents[1]
F, B, BL = Font(name="Arial"), Font(name="Arial", bold=True), Font(name="Arial", color="0000FF")
Y = PatternFill("solid", fgColor="FFFF00")
wb = Workbook(); ws = wb.active; ws.title = "Business case"
ws["A1"] = "Fit badge: returns avoided per 1M orders (illustrative, not Myntra data)"; ws["A1"].font = B
ws.append([]); ws.append(["Input", "Low", "Base", "High", "Source / note"])
for c in ws[3]:
    c.font = B
inputs = [
    ("Orders in scope (fashion, per month)", 1_000_000, 1_000_000, 1_000_000, "ASSUMPTION: scale to Myntra's real volume", "#,##0"),
    ("Return rate, fashion orders", 0.25, 0.30, 0.35, "Return Prime data via Apparel Resources (Jul 2024): 30-35% for clothing and shoes; Shipmozo: 25-40%", "0%"),
    ("Share of returns due to size / fit", 0.35, 0.40, 0.50, "Return Prime: ~40%; Myntra co-founder (Business Insider): nearly 50% from inconsistent sizing", "0%"),
    ("Share of orders on products with a badge", 0.30, 0.43, 0.55, "This repo: badged products hold 43% of fit reviews (rule >=5 reviews, 65% agree)", "0%"),
    ("Shoppers who see the badge and act on it", 0.15, 0.25, 0.40, "ASSUMPTION: to be measured in the A/B test", "0%"),
    ("Fit returns avoided when they act on it", 0.20, 0.30, 0.40, "ASSUMPTION; badge agrees with later shoppers 87% of the time (this repo)", "0%"),
    ("Average order value (Rs)", 1000, 1200, 1500, "ASSUMPTION", "#,##0"),
    ("Cost to process a return, % of item value", 0.20, 0.30, 0.45, "Shipmozo guide: 20-65% of item value", "0%"),
]
for i, (lab, lo, ba, hi, src, fmt) in enumerate(inputs, 4):
    ws.cell(i, 1, lab).font = F
    for j, v in enumerate([lo, ba, hi], 2):
        c = ws.cell(i, j, v); c.font = BL; c.number_format = fmt
        if j == 3:
            c.fill = Y
    ws.cell(i, 5, src).font = F
r = 4 + len(inputs) + 1
ws.cell(r, 1, "Output").font = B
outs = [("Fit returns today", "={c}4*{c}5*{c}6", "#,##0"),
        ("Fit returns avoided", "={c}4*{c}5*{c}6*{c}7*{c}8*{c}9", "#,##0"),
        ("% of all returns avoided", "=IF({c}4*{c}5=0,0,{c}{a}/({c}4*{c}5))", "0.0%"),
        ("Return cost saved (Rs, per month)", "={c}{a}*{c}10*{c}11", "#,##0"),
        ("Return cost saved (Rs crore, per year)", "={c}{s}*12/10000000", "0.00")]
rows = {}
for k, (lab, f, fmt) in enumerate(outs, r + 1):
    ws.cell(k, 1, lab).font = F; rows[lab] = k
for k, (lab, f, fmt) in enumerate(outs, r + 1):
    for j, col in enumerate("BCD", 2):
        c = ws.cell(k, j, f.format(c=col, a=rows["Fit returns avoided"], s=rows["Return cost saved (Rs, per month)"]))
        c.font = F; c.number_format = fmt
ws.cell(r + 7, 1, "Read: the badge is a small lever (about 0.3-4% of all returns) that is cheap to build. The A/B test measures the two ASSUMPTION rows that matter most.").font = F
ws.column_dimensions["A"].width = 42; ws.column_dimensions["E"].width = 95
for col in "BCD":
    ws.column_dimensions[col].width = 14
wb.save(ROOT / "fit_badge_business_case.xlsx"); print("saved")
