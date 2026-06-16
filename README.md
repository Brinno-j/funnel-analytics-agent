# Funnel Analytics Agent

Statistical analysis of e-commerce purchase funnel drop-off across 42 million events,
with full experimentation integrity validation.

---

## Overview

This project identifies where users drop off in a view → cart → purchase funnel,
quantifies conversion gaps across product categories, and validates findings using
a rigorous statistical testing pipeline.

**Dataset:** Kaggle E-Commerce Behavior Data (mkechinov) · October 2019  
**Scale:** 42,448,764 events · 3,022,290 unique users · 166,794 products

---

## Key Findings

### Overall Funnel

| Stage | Unique Users | Conversion Rate |
|---|---|---|
| View | 3,022,130 | — |
| Cart | 337,117 | 11.15% of viewers |
| Purchase | 347,118 | 11.49% of viewers |

Note: purchase count exceeds cart count due to a direct buy-now path that bypasses cart.
View-to-purchase is used as the primary conversion metric throughout.

### Category Breakdown

| Category | Viewers | Conversion | vs Site Average |
|---|---|---|---|
| Electronics | 1,683,322 | 11.88% | +0.39pp |
| Appliances | 544,299 | 9.05% | -2.44pp |
| Computers | 248,605 | 6.52% | -4.97pp |
| Furniture | 202,651 | 2.79% | -8.70pp |
| Apparel | 259,014 | 2.00% | -9.49pp |

### Statistical Validation — Electronics vs Apparel

| Metric | Value |
|---|---|
| Observed gap | 9.88pp |
| Z-test statistic | 152.29 |
| P-value | < 0.0001 |
| 95% Confidence interval | 9.77pp – 9.98pp |
| Sample size needed (1pp lift, 80% power) | 3,077 users |
| Apparel viewers available | 259,014 users |
| Test status | Adequately powered |

The gap is statistically significant and precisely estimated.
The tight CI (9.77–9.98pp) confirms the effect size is reliable, not just directional.

---

## Experimentation Integrity Checks

Standard funnel analyses report conversion rates.
This project also validates the statistical conditions under which those findings can be trusted.

### Peeking Problem Simulation

Simulated 1,000 A/B test runs with daily result checking and no true effect.
Under daily peeking, false positive rate inflated from the nominal 5% to **28.3%** —
meaning more than 1 in 4 significant findings would be noise.
Simulation run on actual dataset user volumes, not synthetic data.

### mSPRT Sequential Testing

Applied a mixture Sequential Probability Ratio Test (mSPRT) as an alternative
to the standard z-test under continuous monitoring.
False positive rate reduced from 28.3% to **10.0%** under identical peeking conditions.
mSPRT allows valid inference at any sample size — eliminating the need to
pre-commit to a fixed stopping point.

### Bonferroni Correction

Z-tests run simultaneously across all 10 category segments vs site average.
Without correction, family-wise false positive rate: ~40%.
With Bonferroni (adjusted alpha = 0.005): all 10 findings remained significant.

### Simpson's Paradox Check

Electronics aggregate conversion (11.88%) is driven by smartphones (12.34% conversion,
1.3M viewers). Several electronics subcategories — camera (2.15%), audio acoustic (2.34%) —
convert at rates comparable to apparel. No directional reversal detected,
but the composition effect is a material caveat on the category-level finding.

---

## Project Structure

| File | Description |
|---|---|
| `load_data.py` | Chunked CSV ingestion into SQLite (300K rows/chunk) |
| `funnel_analysis.py` | Funnel conversion rates by stage and category, bar chart |
| `stats_validation.py` | Two-proportion z-test, 95% CI, retroactive power analysis |
| `experimentation.py` | Peeking simulation, mSPRT, Bonferroni correction, Simpson's paradox |

---

## Reproducing the Analysis

```bash
git clone https://github.com/Brinno-j/funnel-analytics-agent
cd funnel-analytics-agent
pip install -r requirements.txt

# Download dataset via Kaggle CLI
kaggle datasets download -d mkechinov/ecommerce-behavior-data-from-multi-category-store -p data/

# Run in sequence
python load_data.py
python funnel_analysis.py
python stats_validation.py
python experimentation.py
```

---

## Technical Stack

Python · pandas · SQLite · statsmodels · scipy · matplotlib · numpy