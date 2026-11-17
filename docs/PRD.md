# PRD: Review-based Fit Badge on the Product Page

**Author:** Pavitra Seth · **Status:** proposal (built for Myntra's PS-II PM brief) · **Evidence:** this repo

## 1. Problem
Shoppers can't try clothes on, so they guess their size. A wrong guess means a return: reverse logistics
cost, a refund, a lost sale and a less trusting customer. Other shoppers often already know the answer
("runs small, size up"), but it's buried in reviews most people never read.

Evidence (23,486 real fashion reviews, used as a proxy for Myntra's data):
- 36% of reviews that mention a return also mention fit.
- "Runs large" raises the odds of a return mention 1.75×, "runs small" 1.43×, controlling for category; an unflattering cut 2.31×.
- 24% of reviews are unhappy; fit, fabric and "looks different from the photo" lead what they talk about.

## 2. Users and job to be done
- **Shopper on the product page:** "Tell me quickly which size to pick, so I don't have to return it."
- **Category manager:** "Show me which of my products have fit problems, so I can fix the size chart or talk
  to the brand."
- **Returns / logistics team:** fewer fit returns, fewer reverse pickups.

## 3. Solution
A small badge under the size selector: **"Runs small · 76% of 101 shoppers who mentioned fit"**, with one
line of advice ("most suggest one size up") and an expandable "what shoppers said" with 2 review lines.

Rules:
- Show only when ≥5 reviews mention fit **and** ≥65% agree on a direction. Otherwise show nothing.
- Three states: runs small, runs large, true to size.
- Recompute daily; hide if fresh reviews flip the direction.

**Why this rule:** on held-out reviews it agreed with later shoppers 87% of the time vs 61% for a naive
baseline (README). Wrong badges cause returns, so accuracy beats coverage at launch.

Out of scope for v1: personal size recommendation from body measurements or past purchases (v2; the badge
becomes one input to it).

## 4. KPI tree
**North star:** fit-related return rate on badged products.

| Level | Metric |
| --- | --- |
| Primary | Return rate with reason "size/fit" on badged products |
| Secondary | Size-change exchange rate; conversion (PDP → order); share of orders in the badge's suggested direction |
| Guardrails | Overall conversion must not fall > 0.5 pt; non-fit returns flat; page load time flat; badge complaint rate |
| Health | % of PDP views with a badge (coverage); badge flip rate per week |

## 5. A/B test
- **Unit:** user (not session), so a shopper sees the same version every time.
- **Arms:** control (no badge) vs badge. Only products that qualify for a badge enter the analysis, in both arms.
- **Sample size** (two-proportion test, 80% power, 5% significance), orders per arm:

| Fit-return rate today | Detect a drop of | Orders per arm |
| --- | --- | --- |
| 15% | 1.0 pt | 19,436 |
| 15% | 0.5 pt | 78,863 |
| 25% | 1.0 pt | 29,001 |
| 25% | 0.5 pt | 116,809 |

- **Duration:** at least two full weeks (weekday and weekend shopping differ) plus the return window,
  because returns arrive days after the order. Read the primary metric only after the window closes.
- **Pre-registered decision:** ship if fit returns fall significantly and no guardrail breaks. If conversion
  falls but returns also fall, compute net margin per order before deciding.
- **Watch for:** novelty effect (compare week 1 vs week 2); heavy-review categories dominating the result
  (report by category).

## 6. Rollout plan (SOP)
1. **Launch categories:** Dresses, Knits (mostly runs large), Blouses. These have the most fit complaints.
2. **Internal check:** category managers review the badges for their top 50 products; a wrong badge can
   be overridden manually.
3. **Experiment:** 50/50 on qualifying products for the length above.
4. **Ramp:** 10% → 50% → 100%, with guardrail dashboards checked at each step.
5. **Kill switch:** a feature flag per category.
6. **Follow-up:** a weekly "fit problem" list per category for brands (products with strong badges are a
   sizing fix waiting to happen).

## 7. Risks
| Risk | Mitigation |
| --- | --- |
| Wrong badge causes returns | Minimum-evidence rule; daily recompute; manual override |
| Brands dislike "runs small" labels | Frame as help ("size up"), share the list with brands first |
| Badge lowers conversion | Guardrail metric; test measures it directly |
| Text rules miss Hinglish or regional phrasing | Audit sample per language; move to a small classifier trained on labelled reviews |

## 8. Release note (draft)
> **New: know your size before you buy.** Product pages now show how other shoppers found the fit,
> "runs small", "runs large" or "true to size", based on their reviews. Pick the right size the first time.

## 9. Business case and what comes next
- **Size of the prize** (`fit_badge_business_case.xlsx`): per 1M fashion orders a month, about 3,900 fit
  returns avoided and ₹1.7 Cr a year in return costs in the base case (₹0.2–12.5 Cr range). Two inputs are
  assumptions (how many shoppers act on the badge, and how often that avoids a return); the A/B test
  measures both, so the business case gets rewritten with real numbers after the test.
- **v1.1, Bayesian confidence:** replace the two fixed thresholds with one confidence dial (posterior
  probability that the product runs small, empirical-Bayes prior). Same accuracy, 26% more products badged.
- **v2, "how it looks on different bodies":** the strongest return predictor in the data is an
  unflattering cut (odds ratio 2.31), which a size badge can't fix. Show shopper photos tagged with
  height and usual size, plus the model's size and height. Metric: returns with reason "didn't suit me" /
  "looks different".
- **v3, personal size advice:** combine the badge with each shopper's past kept and returned sizes per brand.
