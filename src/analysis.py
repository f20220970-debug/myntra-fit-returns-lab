"""Size-and-fit friction from real fashion reviews: what drives bad ratings and returns, and does a
review-based "fit badge" predict how the next shoppers will find the fit?

Data: 23,486 real customer reviews from a women's fashion e-commerce site (public 'Women's E-Commerce
Clothing Reviews' dataset, 1,206 products, 20 clothing classes). Myntra's own data is private, so this is a
proxy: the method transfers, the exact numbers will differ.

Run: python src/analysis.py  -> results/*.csv, results/summary.json
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

# ----------------------------------------------------------------- friction taxonomy (transparent rules)
# Each theme is a list of phrases. Kept deliberately simple and readable so a PM can audit and extend it.
NEG = r"(?<!not )(?<!not too )(?<!n't )(?<!never )(?<!not at all )(?<!wasn't )(?<!isn't )(?<!n't too )(?<!n't be )"
THEMES = {
    "fit_small": [r"runs? small", r"too small", r"too tight", r"size(d)? up", r"order(ed)? a size up", r"smaller than",
                  r"(?<!not )(?<!not too )\btight\b", r"snug", r"could(n't| not) (button|zip)"],
    "fit_large": [r"runs? (large|big)", r"too (big|large|loose)", r"size(d)? down", r"order(ed)? a size down",
                  r"bigger than", r"(?:is|was|it.s|are|were|felt|looked) (?:so |way |just |really )?huge\b(?! (?:fan|bonus|plus|hit|selling))", r"boxy", r"swallowed me", r"\btent\b", r"swimming in"],
    "length": [r"too (long|short)", r"\blength\b", r"hit(s)? (me )?(at|below|above)", r"petite"],
    "fabric_quality": [r"\bthin\b", r"\bcheap",  r"see[- ]?through", r"sheer", r"itchy", r"scratchy", r"\bpill(ing|s|ed)?\b", r"flimsy",
                       r"poor quality", r"fell apart", r"ripped", r"\bhole\b"],
    "looks_different": [r"(not|nothing) like (the )?(picture|photo|pic)", r"looks? different", r"in the (photo|picture)",
                        r"on the model", r"online", r"\bpictured\b"],
    # added after the TF-IDF check in deep.py found these among the strongest unhappy words the rules missed
    "unflattering_cut": [r"unflattering", r"frumpy", r"shapeless", r"maternity", r"no shape", r"potato sack", r"\bodd\b", r"\bweird\b"],
    "colour": [r"\bcolou?r\b", r"darker than", r"lighter than", r"washed out"],
    "price": [r"\bprice", r"expensive", r"overpriced", r"not worth", r"on sale"],
}
RETURN = r"\breturn(?:ed|ing|s)?\b|sent (?:it|them) back|send (?:it|them) back|going back|went back"


GUARDED = {"fit_small", "fit_large", "fabric_quality", "unflattering_cut"}   # negation guard: "not too tight", "isn't boxy", "not thin"


def _pattern(k, v):
    return "|".join(f"{NEG}(?:{p})" if k in GUARDED else f"(?:{p})" for p in v)


def tag(text: pd.Series) -> pd.DataFrame:
    t = text.fillna("").str.lower()
    out = pd.DataFrame({k: t.str.contains(_pattern(k, v), regex=True) for k, v in THEMES.items()})
    out["fit_any"] = out.fit_small | out.fit_large
    out["mentions_return"] = t.str.contains(RETURN, regex=True)
    return out


def main():
    d = pd.read_csv(ROOT / "data" / "womens_clothing_reviews.csv").rename(columns=lambda c: c.strip())
    d = d[d["Review Text"].notna()].copy()
    tags = tag(d["Title"].fillna("") + ". " + d["Review Text"])
    d = d.join(tags)
    d["unhappy"] = (d.Rating <= 3) | (d["Recommended IND"] == 0)
    S = {"reviews_with_text": int(len(d)), "products": int(d["Clothing ID"].nunique()),
         "unhappy_share": round(float(d.unhappy.mean()), 3),
         "return_mention_share": round(float(d.mentions_return.mean()), 3)}

    # 1. What do unhappy customers talk about, vs happy ones?
    themes = list(THEMES) + ["fit_any"]
    rows = []
    for th in themes:
        u, h = d.loc[d.unhappy, th].mean(), d.loc[~d.unhappy, th].mean()
        rr = d.loc[d[th], "mentions_return"].mean()
        rows.append({"theme": th, "pct_of_unhappy_reviews": round(100 * u, 1), "pct_of_happy_reviews": round(100 * h, 1),
                     "lift_unhappy_vs_happy": round(u / h, 2) if h else None,
                     "pct_mentioning_return_when_theme_present": round(100 * rr, 1)})
    drivers = pd.DataFrame(rows).sort_values("pct_of_unhappy_reviews", ascending=False)
    drivers.to_csv(RES / "friction_drivers.csv", index=False)

    # 2. What predicts a return mention? (logistic regression, odds ratios, controlling for class)
    X = pd.get_dummies(d[list(THEMES)].astype(int).join(d[["Class Name"]].fillna("Other")), columns=["Class Name"],
                       drop_first=True, dtype=int)
    y = d.mentions_return.astype(int)
    lr = LogisticRegression(max_iter=2000, C=1.0).fit(X, y)
    odds = pd.Series(np.exp(lr.coef_[0]), index=X.columns)
    odds_themes = odds[list(THEMES)].sort_values(ascending=False).round(2)
    odds_themes.rename("odds_ratio_for_return_mention").to_csv(RES / "return_odds_ratios.csv")
    # share of return mentions that involve a fit problem
    ret = d[d.mentions_return]
    S["share_of_return_mentions_with_fit_issue"] = round(float(ret.fit_any.mean()), 3)
    S["share_of_return_mentions_with_fabric_issue"] = round(float(ret.fabric_quality.mean()), 3)

    # 3. Which categories should a fit feature launch in first?
    cls = d.groupby("Class Name").agg(reviews=("ID", "size"), fit_issue_pct=("fit_any", "mean"),
                                      small_pct=("fit_small", "mean"), large_pct=("fit_large", "mean"),
                                      return_pct=("mentions_return", "mean"), unhappy_pct=("unhappy", "mean"))
    cls = cls[cls.reviews >= 300]
    cls["fit_issue_reviews"] = (cls.reviews * cls.fit_issue_pct).round(0)
    for c in ["fit_issue_pct", "small_pct", "large_pct", "return_pct", "unhappy_pct"]:
        cls[c] = (100 * cls[c]).round(1)
    cls = cls.sort_values("fit_issue_reviews", ascending=False)
    cls.to_csv(RES / "category_priority.csv")

    # 4. Fit badge: label each product from 70% of its reviews, test on the other 30%
    rng = np.random.default_rng(0)
    d["split"] = np.where(rng.random(len(d)) < 0.7, "build", "test")
    fit = d[d.fit_small ^ d.fit_large].copy()                 # reviews that clearly say small OR large
    fit["direction"] = np.where(fit.fit_small, "small", "large")
    counts = fit.groupby(["Clothing ID", "split", "direction"]).size().unstack(fill_value=0)
    b = counts.xs("build", level="split").reindex(columns=["small", "large"], fill_value=0)
    t = counts.xs("test", level="split").reindex(columns=["small", "large"], fill_value=0)
    prod = b.join(t, lsuffix="_build", rsuffix="_test", how="inner")
    prod["n_build"] = prod.small_build + prod.large_build
    prod["n_test"] = prod.small_test + prod.large_test
    res = []
    for min_votes, margin in [(3, 0.6), (5, 0.65), (8, 0.7)]:
        p = prod[(prod.n_build >= min_votes) & (prod.n_test >= 2)].copy()
        p["share_small_build"] = p.small_build / p.n_build
        p["badge"] = np.where(p.share_small_build >= margin, "small",
                              np.where(p.share_small_build <= 1 - margin, "large", "mixed"))
        p["test_majority"] = np.where(p.small_test > p.large_test, "small",
                                      np.where(p.large_test > p.small_test, "large", "tie"))
        badged = p[(p.badge != "mixed") & (p.test_majority != "tie")]
        # baseline: always say the most common direction overall ("runs small" is more common or not)
        overall = "small" if fit.direction.eq("small").mean() >= 0.5 else "large"
        res.append({"min_fit_reviews_to_badge": min_votes, "agreement_needed": margin,
                    "products_badged": int(len(badged)),
                    "badge_agrees_with_later_shoppers_pct": round(100 * float((badged.badge == badged.test_majority).mean()), 1),
                    "baseline_always_say_" + overall + "_pct": round(100 * float((badged.test_majority == overall).mean()), 1),
                    "fit_reviews_on_badged_products_pct": round(100 * float(badged.n_test.sum() / max(prod.n_test.sum(), 1)), 1)})
    badge_eval = pd.DataFrame(res)
    badge_eval.to_csv(RES / "fit_badge_evaluation.csv", index=False)
    S["fit_reviews_clear_direction"] = int(len(fit))
    S["share_of_fit_reviews_saying_small"] = round(float(fit.direction.eq("small").mean()), 3)

    # 5. Experiment design for a fit-badge A/B test (sample size per arm, two-proportion test, 80% power, 5% alpha)
    def n_per_arm(p1, mde):
        p2 = p1 - mde
        z = 1.96 + 0.84
        return int(np.ceil(z ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / mde ** 2))
    S["ab_test_orders_per_arm"] = {f"base_{int(b * 100)}pct_detect_{m}pt": n_per_arm(b, m / 100)
                                   for b in [0.15, 0.25] for m in [0.5, 1.0]}

    # 6. Badges for the prototype: built from ALL reviews with the chosen rule (min 5 fit reviews, 65% agreement)
    allp = fit.groupby(["Clothing ID", "direction"]).size().unstack(fill_value=0).reindex(columns=["small", "large"], fill_value=0)
    allp["n"] = allp.small + allp.large
    allp = allp[allp.n >= 5]
    allp["share_small"] = allp.small / allp.n
    allp["badge"] = np.where(allp.share_small >= .65, "runs small", np.where(allp.share_small <= .35, "runs large", "true to size / mixed"))
    meta = d.groupby("Clothing ID").agg(cls=("Class Name", "first"), reviews=("ID", "size"), rating=("Rating", "mean"),
                                        return_pct=("mentions_return", "mean"))
    allp = allp.join(meta)
    allp.to_csv(RES / "fit_badges_all_products.csv")
    S["badge_distribution"] = allp.badge.value_counts().to_dict()
    S["return_pct_by_badge"] = (100 * fit.join(allp.badge, on="Clothing ID").groupby("badge").mentions_return.mean()).round(1).to_dict()

    S["drivers_top"] = drivers.head(5).to_dict(orient="records")
    S["return_odds"] = odds_themes.to_dict()
    S["category_top"] = cls.head(6).reset_index().to_dict(orient="records")
    S["badge_eval"] = badge_eval.to_dict(orient="records")
    (RES / "summary.json").write_text(json.dumps(S, indent=1, default=float))
    pd.set_option("display.width", 200)
    print(json.dumps({k: v for k, v in S.items() if not isinstance(v, list)}, indent=1, default=float))
    print(drivers.to_string(index=False)); print(odds_themes.to_string()); print(cls.to_string()); print(badge_eval.to_string(index=False))


if __name__ == "__main__":
    main()
