"""Charts for the README: python src/plot.py -> docs/results.png"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
(ROOT / "docs").mkdir(exist_ok=True)

drv = pd.read_csv(R / "friction_drivers.csv")
drv = drv[drv.theme != "fit_any"].sort_values("pct_of_unhappy_reviews")
odds = pd.read_csv(R / "return_odds_ratios.csv", index_col=0).iloc[:, 0].sort_values()
cls = pd.read_csv(R / "category_priority.csv").head(8).iloc[::-1]
badge = pd.read_csv(R / "fit_badge_evaluation.csv")

fig, ax = plt.subplots(1, 4, figsize=(19, 4.6))
y = range(len(drv))
ax[0].barh([i + .2 for i in y], drv.pct_of_unhappy_reviews, .4, label="unhappy reviews", color="#d9534f")
ax[0].barh([i - .2 for i in y], drv.pct_of_happy_reviews, .4, label="happy reviews", color="#9aa5b1")
ax[0].set_yticks(list(y), drv.theme); ax[0].set_xlabel("% of reviews mentioning"); ax[0].legend(fontsize=8)
ax[0].set_title("1. What unhappy shoppers talk about")

ax[1].barh(odds.index, odds.values, color=["#d9534f" if v > 1.2 else "#9aa5b1" for v in odds.values])
ax[1].axvline(1, color="k", lw=.8); ax[1].set_xlabel("odds ratio (controls for category)")
ax[1].set_title("2. What predicts a return mention")

ax[2].barh(cls["Class Name"], cls.small_pct, color="#5b8def", label="runs small")
ax[2].barh(cls["Class Name"], cls.large_pct, left=cls.small_pct, color="#f0ad4e", label="runs large")
ax[2].set_xlabel("% of reviews with a fit complaint"); ax[2].legend(fontsize=8)
ax[2].set_title("3. Where to launch first (by volume)")

base_col = [c for c in badge.columns if c.startswith("baseline")][0]
lab = [f"≥{m} reviews\n{a:.0%} agree\n({p} products)" for m, a, p in
       zip(badge.min_fit_reviews_to_badge, badge.agreement_needed, badge.products_badged)]
x = range(len(badge))
ax[3].bar([i - .2 for i in x], badge.badge_agrees_with_later_shoppers_pct, .4, label="fit badge", color="#2e7d32")
ax[3].bar([i + .2 for i in x], badge[base_col], .4, label="always 'runs large'", color="#9aa5b1")
ax[3].set_xticks(list(x), lab, fontsize=8); ax[3].set_ylim(50, 100); ax[3].set_ylabel("% agreeing with later shoppers")
ax[3].legend(fontsize=8); ax[3].set_title("4. Fit badge on held-out reviews")
plt.tight_layout()
plt.savefig(ROOT / "docs" / "results.png", dpi=130)
print("saved docs/results.png")
