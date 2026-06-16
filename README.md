# Funnel Analytics Agent

A statistical analysis of where users drop off in an e-commerce purchase funnel — and whether those drop-offs are real or just noise.

---

## The question

A product team wants to know: which categories have the worst conversion, and can we trust that finding statistically?

This project answers that using 42 million real e-commerce events from October 2019.

---

## What I found

Overall, 11.49% of users who viewed a product went on to purchase something.

But that average hides a big gap between categories:

| Category | Conversion | vs Average |
|---|---|---|
| Electronics | 11.88% | +0.39pp |
| Appliances | 9.05% | -2.44pp |
| Computers | 6.52% | -4.97pp |
| Apparel | 2.00% | -9.49pp |

Apparel converts at 2% vs electronics at 11.88% — a 9.88pp gap. I ran a z-test to confirm this isn't random noise: p < 0.0001, 95% CI: 9.77–9.98pp. The gap is real and precisely estimated.

A retroactive power analysis showed we only needed 3,077 users per segment to detect a 1pp lift at 80% power. We had 259,014 apparel users — the finding is rock solid.

---

## The experimentation integrity checks

Most funnel analyses stop at the conversion rate. This one goes further.

**Peeking problem:** If a team checks experiment results daily and stops when p < 0.05, the false positive rate inflates from 5% to 28.3%. I simulated this on the actual dataset across 1,000 runs to show the inflation on real data, not just theory.

**mSPRT sequential testing:** The correct solution to peeking. Using a likelihood ratio approach instead of a fixed p-value, false positives dropped from 28.3% to 10.0% under the same daily checking conditions.

**Bonferroni correction:** Running z-tests across all 10 category segments simultaneously. Without correction the family-wise false positive rate would be ~40%. All 10 findings survived Bonferroni correction.

**Simpson's paradox check:** Electronics looks strong overall because smartphones alone convert at 12.34% and dominate the category. Several electronics subcategories (camera, audio acoustic) convert at 2.1–2.3% — close to apparel rates. No paradox detected, but the composition effect is worth flagging.

---

## Dataset

[E-Commerce Behavior Data — Kaggle](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store)

42,448,764 events · 3,022,290 unique users · 166,794 products · October 2019

---

## How to run

```bash
git clone https://github.com/Brinno-j/funnel-analytics-agent
cd funnel-analytics-agent
pip install -r requirements.txt

# Download dataset from Kaggle and place in data/
python load_data.py        # Load into SQLite
python funnel_analysis.py  # Funnel by stage and category
python stats_validation.py # Z-test, CI, power analysis
python experimentation.py  # Peeking, mSPRT, Bonferroni, Simpson's paradox
```

---

## Files

| File | What it does |
|---|---|
| `load_data.py` | Loads 42M rows into SQLite via chunked pandas processing |
| `funnel_analysis.py` | Funnel conversion rates by stage and category |
| `stats_validation.py` | Z-test, confidence interval, power analysis |
| `experimentation.py` | Peeking simulation, mSPRT, Bonferroni correction, Simpson's paradox |