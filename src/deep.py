"""Deeper checks on the fit badge and the taxonomy.

1. Bayesian badge: a Beta-Binomial model (prior fitted across all products, empirical Bayes) gives each product a
   posterior probability that it runs small. Show a badge only when that probability is >= tau. Compared with
   the fixed rules on the SAME 70/30 split: precision (agreement with later shoppers) vs coverage.
2. Uncertainty: bootstrap 95% CI (resampling products) for the chosen rule's agreement and the baseline.
3. Learning curve: how many fit reviews before a badge is reliable?
4. What did my phrase rules miss? A TF-IDF logistic regression predicting an unhappy review; the strongest
   words that none of my themes cover.
Run: python src/deep.py -> results/deep_*.csv, results/deep_summary.json, docs/deep.png
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import betaln
from scipy.stats import beta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from analysis import THEMES, tag

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"


def split_counts():
    d = pd.read_csv(ROOT / "data" / "womens_clothing_reviews.csv")
    d = d[d["Review Text"].notna()].copy()
    d = d.join(tag(d["Title"].fillna("") + ". " + d["Review Text"]))
    rng = np.random.default_rng(0)                           # same split as analysis.py
    d["split"] = np.where(rng.random(len(d)) < 0.7, "build", "test")
    fit = d[d.fit_small ^ d.fit_large].copy()
    fit["direction"] = np.where(fit.fit_small, "small", "large")
    c = fit.groupby(["Clothing ID", "split", "direction"]).size().unstack(fill_value=0)
    b = c.xs("build", level="split").reindex(columns=["small", "large"], fill_value=0)
    t = c.xs("test", level="split").reindex(columns=["small", "large"], fill_value=0)
    p = b.join(t, lsuffix="_b", rsuffix="_t", how="inner")
    p["n_b"], p["n_t"] = p.small_b + p.large_b, p.small_t + p.large_t
    p = p[(p.n_t >= 2) & (p.small_t != p.large_t)]
    p["truth"] = np.where(p.small_t > p.large_t, "small", "large")
    return d, p


def fit_prior(k, n):
    """Empirical-Bayes Beta(a, b) prior for 'share saying small', by maximising the Beta-Binomial likelihood."""
    def nll(x):
        a, b_ = np.exp(x)
        return -np.sum(betaln(k + a, n - k + b_) - betaln(a, b_))
    a, b_ = np.exp(minimize(nll, [0, 0], method="Nelder-Mead").x)
    return a, b_


def main():
    d, p = split_counts()
    S = {}
    a, b_ = fit_prior(p.small_b.values, p.n_b.values)
    S["prior_alpha_beta"] = [round(a, 2), round(b_, 2)]
    S["prior_mean_small"] = round(a / (a + b_), 3)
    p["p_small"] = 1 - beta.cdf(0.5, a + p.small_b, b_ + p.large_b)   # posterior P(more shoppers say small)
    total = len(p)
    rows = []
    for tau in [0.8, 0.85, 0.9, 0.95, 0.975, 0.99]:
        badge = np.where(p.p_small >= tau, "small", np.where(p.p_small <= 1 - tau, "large", None))
        m = badge != None  # noqa: E711
        rows.append({"rule": f"Bayesian, P >= {tau}", "products_badged": int(m.sum()),
                     "coverage_pct": 100 * m.sum() / total, "agreement_pct": 100 * (badge[m] == p.truth[m]).mean()})
    for mv, mg in [(3, .6), (5, .65), (8, .7)]:
        sh = p.small_b / p.n_b.clip(lower=1)
        badge = np.where((p.n_b >= mv) & (sh >= mg), "small", np.where((p.n_b >= mv) & (sh <= 1 - mg), "large", None))
        m = badge != None  # noqa: E711
        rows.append({"rule": f"fixed: >= {mv} reviews, {int(mg*100)}% agree", "products_badged": int(m.sum()),
                     "coverage_pct": 100 * m.sum() / total, "agreement_pct": 100 * (badge[m] == p.truth[m]).mean()})
    cmp_ = pd.DataFrame(rows).round(1)
    cmp_.to_csv(RES / "deep_badge_rules.csv", index=False)

    # bootstrap CI for the fixed (5, 65%) rule and the always-"large" baseline, resampling products
    sh = p.small_b / p.n_b.clip(lower=1)
    badge = np.where((p.n_b >= 5) & (sh >= .65), "small", np.where((p.n_b >= 5) & (sh <= .35), "large", None))
    m = badge != None  # noqa: E711
    ok = (badge[m] == p.truth[m]).values.astype(float); base = (p.truth[m] == "large").values.astype(float)
    rng = np.random.default_rng(1); bs = []
    for _ in range(5000):
        ix = rng.integers(0, len(ok), len(ok)); bs.append((ok[ix].mean(), base[ix].mean(), ok[ix].mean() - base[ix].mean()))
    bs = np.array(bs)
    S["chosen_rule_products"] = int(m.sum())
    S["chosen_rule_agreement_pct_95ci"] = [round(100 * float(np.percentile(bs[:, 0], q)), 1) for q in (2.5, 50, 97.5)]
    S["baseline_pct_95ci"] = [round(100 * float(np.percentile(bs[:, 1], q)), 1) for q in (2.5, 50, 97.5)]
    S["gain_pp_95ci"] = [round(100 * float(np.percentile(bs[:, 2], q)), 1) for q in (2.5, 50, 97.5)]

    # learning curve: Bayesian rule at tau=0.9, agreement by number of fit reviews available when the badge is set
    tau = 0.9
    badge = np.where(p.p_small >= tau, "small", np.where(p.p_small <= 1 - tau, "large", None))
    p["badge"] = badge
    p["n_bin"] = pd.cut(p.n_b, [0, 4, 9, 19, 1000], labels=["1-4", "5-9", "10-19", "20+"])
    lc = p.groupby("n_bin", observed=True).apply(lambda g: pd.Series({
        "products": len(g), "badged_pct": 100 * g.badge.notna().mean(),
        "agreement_when_badged_pct": 100 * (g.badge[g.badge.notna()] == g.truth[g.badge.notna()]).mean() if g.badge.notna().any() else np.nan}),
        include_groups=False).round(1)
    lc.to_csv(RES / "deep_learning_curve.csv")

    # what did the rules miss? TF-IDF + logistic regression for 'unhappy'
    text = (d["Title"].fillna("") + ". " + d["Review Text"]).str.lower()
    y = ((d.Rating <= 3) | (d["Recommended IND"] == 0)).astype(int)
    Xtr, Xte, ytr, yte = train_test_split(text, y, test_size=0.3, random_state=0, stratify=y)
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=20, stop_words="english", sublinear_tf=True)
    lr = LogisticRegression(max_iter=3000, C=2).fit(vec.fit_transform(Xtr), ytr)
    S["tfidf_unhappy_auc"] = round(float(roc_auc_score(yte, lr.predict_proba(vec.transform(Xte))[:, 1])), 3)
    rule_cols = list(THEMES)
    rlr = LogisticRegression(max_iter=2000).fit(tag(Xtr)[rule_cols].astype(int), ytr)
    S["rules_only_unhappy_auc"] = round(float(roc_auc_score(yte, rlr.predict_proba(tag(Xte)[rule_cols].astype(int))[:, 1])), 3)
    from analysis import RETURN
    allpat = re.compile("|".join([p_ for v in THEMES.values() for p_ in v] + [RETURN, r"disappoint|unfortunately|\bsad\b|\bbad\b|shame|wanted|excited|\bpoor\b"]))
    w = pd.Series(lr.coef_[0], index=vec.get_feature_names_out()).sort_values(ascending=False)
    top = [(t, round(float(c), 2)) for t, c in w.head(80).items()]
    missed = [(t, c) for t, c in top if not allpat.search(t)]
    pd.DataFrame(top, columns=["term", "weight"]).assign(covered_by_rules=[bool(allpat.search(t)) for t, _ in top]) \
        .to_csv(RES / "deep_unhappy_terms.csv", index=False)
    S["top_unhappy_terms_not_in_rules"] = [t for t, _ in missed[:25]]
    (RES / "deep_summary.json").write_text(json.dumps(S, indent=1))
    print(json.dumps(S, indent=1)); print(cmp_.to_string(index=False)); print(lc.to_string())

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bay = cmp_[cmp_.rule.str.startswith("Bayes")]; fx = cmp_[cmp_.rule.str.startswith("fixed")]
    ax.plot(bay.coverage_pct, bay.agreement_pct, "o-", color="#2e7d32", label="Bayesian badge (vary confidence)")
    ax.plot(fx.coverage_pct, fx.agreement_pct, "s--", color="#9aa5b1", label="fixed rules")
    ax.set_xlabel("% of products that get a badge"); ax.set_ylabel("% agreeing with later shoppers")
    ax.set_title("Fit badge: accuracy vs coverage (held-out reviews)"); ax.grid(alpha=.3); ax.legend()
    plt.tight_layout(); plt.savefig(ROOT / "docs" / "deep.png", dpi=130)


if __name__ == "__main__":
    main()
