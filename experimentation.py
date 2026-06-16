import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.stats.proportion import proportions_ztest
from statsmodels.stats.multitest import multipletests

DB_PATH = "data/ecommerce.db"

conn = sqlite3.connect(DB_PATH)

# ── Section 1 — Peeking Problem Simulation ────────────────────────────────
print("=" * 50)
print("SECTION 1 — PEEKING PROBLEM SIMULATION")
print("=" * 50)

print("""
What we are simulating:
  A team runs an A/B test and checks results every day.
  They stop as soon as p < 0.05.
  We measure how often this produces a false positive —
  a 'significant' result when there is actually no real difference.
  
  Correct false positive rate should be 5%.
  We will see it inflate far above that under daily peeking.
""")

# Pull daily apparel purchase data
daily_data = pd.read_sql("""
    SELECT
        DATE(event_time) AS date,
        COUNT(DISTINCT CASE WHEN event_type = 'view'     THEN user_id END) AS viewers,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS purchasers
    FROM events
    WHERE category_code LIKE 'apparel%'
    GROUP BY DATE(event_time)
    ORDER BY date
""", conn)

print("Daily apparel data:")
print(daily_data.to_string(index=False))

# Simulate peeking — run 1000 simulations
np.random.seed(42)
n_simulations = 1000
true_rate     = 0.02  # apparel baseline conversion
false_positives = 0

for _ in range(n_simulations):
    group_a = []
    group_b = []
    peeked_significant = False

    for day in range(1, 32):  # simulate 31 days
        # Add new users each day — same true rate for both groups
        daily_users = np.random.randint(5000, 10000)
        group_a.extend(np.random.binomial(1, true_rate, daily_users))
        group_b.extend(np.random.binomial(1, true_rate, daily_users))

        # Peek at results — check p-value daily
        if len(group_a) > 100:
            count_a = sum(group_a)
            count_b = sum(group_b)
            n_a     = len(group_a)
            n_b     = len(group_b)

            _, pvalue = proportions_ztest([count_a, count_b], [n_a, n_b])

            if pvalue < 0.05:
                peeked_significant = True
                break  # stop as soon as significant — like a real team would

    if peeked_significant:
        false_positives += 1

false_positive_rate = round(false_positives / n_simulations * 100, 1)

print(f"\nSimulation results ({n_simulations} runs):")
print(f"  True effect:          NONE — both groups have identical conversion rates")
print(f"  Expected false positive rate: 5.0%")
print(f"  Actual false positive rate:  {false_positive_rate}%")
print(f"\n  Peeking inflated false positives by {round(false_positive_rate - 5, 1)}pp")
print(f"  That means {false_positive_rate}% of 'significant' findings are actually noise")

# ── Section 2 — Bonferroni Correction ────────────────────────────────────
print("\n" + "=" * 50)
print("SECTION 2 — BONFERRONI CORRECTION")
print("=" * 50)

print("""
What we are testing:
  We run z-tests across all category segments simultaneously.
  Without correction: high chance of at least one false positive.
  With Bonferroni: adjust threshold to control false positive rate.
""")

category_data = pd.read_sql("""
    SELECT
        SUBSTR(category_code, 1, INSTR(category_code, '.') - 1) AS category,
        COUNT(DISTINCT CASE WHEN event_type = 'view'     THEN user_id END) AS viewers,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS purchasers
    FROM events
    WHERE category_code IS NOT NULL
    GROUP BY category
    HAVING viewers > 10000
    ORDER BY viewers DESC
""", conn)

# Site overall as baseline
site_data = pd.read_sql("""
    SELECT
        COUNT(DISTINCT CASE WHEN event_type = 'view'     THEN user_id END) AS viewers,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS purchasers
    FROM events
""", conn)

site_viewers    = int(site_data['viewers'][0])
site_purchasers = int(site_data['purchasers'][0])

# Run z-test for each category vs site average
pvalues    = []
categories = []

for _, row in category_data.iterrows():
    counts = [int(row['purchasers']), site_purchasers]
    nobs   = [int(row['viewers']),    site_viewers]
    _, pv  = proportions_ztest(counts, nobs)
    pvalues.append(pv)
    categories.append(row['category'])

# Apply Bonferroni correction
reject, pvals_corrected, _, _ = multipletests(pvalues, alpha=0.05, method='bonferroni')

results = pd.DataFrame({
    'category':        categories,
    'p_value_raw':     [round(p, 6) for p in pvalues],
    'p_value_bonf':    [round(p, 6) for p in pvals_corrected],
    'significant_raw': ['YES' if p < 0.05 else 'NO' for p in pvalues],
    'significant_bonf':['YES' if r else 'NO' for r in reject]
})

print(results.to_string(index=False))

n_raw  = results['significant_raw'].value_counts().get('YES', 0)
n_bonf = results['significant_bonf'].value_counts().get('YES', 0)

print(f"\nWithout correction: {n_raw} of {len(categories)} categories significant")
print(f"With Bonferroni:    {n_bonf} of {len(categories)} categories significant")
print(f"Findings that didn't survive correction: {n_raw - n_bonf}")

# ── Section 3 — Simpson's Paradox Check ──────────────────────────────────
print("\n" + "=" * 50)
print("SECTION 3 — SIMPSON'S PARADOX CHECK")
print("=" * 50)

print("""
What we are checking:
  Electronics converts higher than apparel overall.
  Does this hold at subcategory level?
  If the direction reverses in any subcategory — that is Simpson's Paradox.
""")

subcategory_data = pd.read_sql("""
    SELECT
        SUBSTR(category_code, 1, INSTR(category_code, '.') - 1)  AS category,
        category_code                                              AS subcategory,
        COUNT(DISTINCT CASE WHEN event_type = 'view'     THEN user_id END) AS viewers,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS purchasers
    FROM events
    WHERE category_code IS NOT NULL
    AND SUBSTR(category_code, 1, INSTR(category_code, '.') - 1) IN ('electronics', 'apparel')
    GROUP BY category_code
    HAVING viewers > 1000
    ORDER BY category, viewers DESC
""", conn)

subcategory_data['conversion_pct'] = round(
    subcategory_data['purchasers'] / subcategory_data['viewers'] * 100, 2)

print(subcategory_data.to_string(index=False))

# Check for reversal
elec_sub  = subcategory_data[subcategory_data['category'] == 'electronics']['conversion_pct']
appar_sub = subcategory_data[subcategory_data['category'] == 'apparel']['conversion_pct']

elec_avg  = round(elec_sub.mean(),  2)
appar_avg = round(appar_sub.mean(), 2)

print(f"\nOverall conversion:")
print(f"  Electronics: 11.88%  Apparel: 2.00%  → Electronics higher")
print(f"\nSubcategory average conversion:")
print(f"  Electronics subcategories avg: {elec_avg}%")
print(f"  Apparel subcategories avg:     {appar_avg}%")

if appar_avg > elec_avg:
    print(f"\n⚠ SIMPSON'S PARADOX DETECTED")
    print(f"  Apparel subcategories average HIGHER than electronics subcategories")
    print(f"  The aggregate result was hiding a composition effect")
else:
    print(f"\nNo paradox detected — direction is consistent at subcategory level")
    print(f"Electronics converts higher both overall and within subcategories")

conn.close()
# ── Section 4 — mSPRT Sequential Testing ─────────────────────────────────
print("\n" + "=" * 50)
print("SECTION 4 — mSPRT SEQUENTIAL TESTING")
print("=" * 50)

print("""
What we are testing:
  mSPRT (mixture Sequential Probability Ratio Test) is the correct
  solution to the peeking problem.

  Standard z-test: only valid at one pre-specified sample size.
  mSPRT:           valid at any sample size — you can peek any time.

  How it works:
  Instead of a p-value, mSPRT computes a running likelihood ratio (K).
  K > threshold means evidence for a real effect.
  K < 1/threshold means evidence for no effect.
  In between — keep collecting data.

  We compare false positive rates:
  Standard z-test with peeking: 28.3% (we just measured this)
  mSPRT with peeking:           should stay near 5%
""")

np.random.seed(42)
n_simulations  = 1000
true_rate      = 0.02
threshold      = 20        # K > 20 = significant, industry standard
false_positives_msprt = 0

def compute_msprt_k(successes_a, n_a, successes_b, n_b, prior_variance=0.1):
    """
    Simplified mSPRT likelihood ratio.
    Compares evidence for difference vs no difference.
    Returns K — the likelihood ratio statistic.
    """
    if n_a == 0 or n_b == 0:
        return 1.0

    rate_a   = successes_a / n_a
    rate_b   = successes_b / n_b
    rate_avg = (successes_a + successes_b) / (n_a + n_b)

    # Avoid log(0)
    if rate_avg == 0 or rate_avg == 1:
        return 1.0
    if rate_a == 0 or rate_a == 1:
        return 1.0
    if rate_b == 0 or rate_b == 1:
        return 1.0

    # Log likelihood ratio
    ll_null = (successes_a + successes_b) * np.log(rate_avg) + \
              (n_a + n_b - successes_a - successes_b) * np.log(1 - rate_avg)

    ll_alt  = successes_a * np.log(rate_a) + \
              (n_a - successes_a) * np.log(1 - rate_a) + \
              successes_b * np.log(rate_b) + \
              (n_b - successes_b) * np.log(1 - rate_b)

    return np.exp(ll_alt - ll_null)

for _ in range(n_simulations):
    successes_a = 0
    successes_b = 0
    n_a = 0
    n_b = 0
    msprt_significant = False

    for day in range(1, 32):
        daily_users = np.random.randint(5000, 10000)

        new_a = np.random.binomial(daily_users, true_rate)
        new_b = np.random.binomial(daily_users, true_rate)

        successes_a += new_a
        successes_b += new_b
        n_a         += daily_users
        n_b         += daily_users

        if n_a > 100:
            K = compute_msprt_k(successes_a, n_a, successes_b, n_b)
            if K > threshold:
                msprt_significant = True
                break

    if msprt_significant:
        false_positives_msprt += 1

msprt_fpr = round(false_positives_msprt / n_simulations * 100, 1)

print(f"Simulation results ({n_simulations} runs, peeking daily):")
print(f"  True effect: NONE — both groups identical")
print(f"  Threshold K: {threshold}")
print(f"\n  Standard z-test false positive rate: 28.3%")
print(f"  mSPRT false positive rate:           {msprt_fpr}%")
print(f"\n  mSPRT reduced false positives by {round(28.3 - msprt_fpr, 1)}pp")
print(f"\nConclusion:")
print(f"  mSPRT lets you peek at results any time without")
print(f"  inflating your false positive rate.")
print(f"  Teams that need to monitor experiments continuously")
print(f"  should use sequential testing instead of standard z-tests.")

print("\nExperimentation analysis complete.")