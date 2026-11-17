import json
from pathlib import Path

import pandas as pd

from analysis import tag, main

ROOT = Path(__file__).resolve().parents[1]


def t(s):
    return tag(pd.Series([s])).iloc[0]


def test_fit_directions():
    assert t("Runs small, I had to size up").fit_small
    assert t("It runs large so order a size down").fit_large
    assert not t("Lovely dress").fit_any


def test_negation_guard():
    assert not t("The waist is not too tight").fit_small
    assert not t("It isn't boxy at all").fit_large
    assert not t("Fabric is not thin").fabric_quality


def test_word_boundaries():
    assert not t("Great content and nothing to complain about").fabric_quality   # 'thin' inside 'nothing'
    assert not t("The content is great").fit_large                             # 'tent' inside 'content'
    assert t("It fit like a tent").fit_large


def test_return_detection():
    assert t("I returned it").mentions_return
    assert t("Sent it back the same day").mentions_return
    assert not t("Will buy again").mentions_return


def test_pipeline_outputs_and_badge_beats_baseline():
    main()
    S = json.loads((ROOT / "results" / "summary.json").read_text())
    assert S["reviews_with_text"] > 20000
    ev = pd.read_csv(ROOT / "results" / "fit_badge_evaluation.csv")
    base = [c for c in ev.columns if c.startswith("baseline")][0]
    assert (ev.badge_agrees_with_later_shoppers_pct > ev[base]).all()
    assert S["ab_test_orders_per_arm"]["base_15pct_detect_1.0pt"] > 10000


def test_unflattering_theme_and_guard():
    assert t("The cut is so unflattering and frumpy").unflattering_cut
    assert not t("It is not unflattering at all").unflattering_cut


def test_bayesian_prior_is_sensible():
    import numpy as np
    from deep import fit_prior
    rng = np.random.default_rng(0)
    p = rng.beta(4, 4, 400); n = rng.integers(5, 40, 400); k = rng.binomial(n, p)
    a, b = fit_prior(k, n)
    assert abs(a / (a + b) - 0.5) < 0.05 and 2 < a < 8
