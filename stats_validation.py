import sqlite3
import pandas as pd
from statsmodels.stats.proportion import proportions_ztest, proportion_confint
from statsmodels.stats.power import NormalIndPower

DB_PATH = "data/ecommerce.db"

conn = sqlite3.connect(DB_PATH)

# ── Section 1 — Pull segment data ─────────────────────────────────────────
print("=" * 50)
print("SECTION 1 — SEGMENT DATA")
print("=" * 50)

segment_data = pd.read_sql("""
    SELECT
        SUBSTR(category_code, 1, INSTR(category_code, '.') - 1) AS category,
        COUNT(DISTINCT CASE WHEN event_type = 'view'     THEN user_id END) AS viewers,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS purchasers
    FROM events
    WHERE category_code IS NOT NULL
    AND SUBSTR(category_code, 1, INSTR(category_code, '.') - 1) IN ('electronics', 'apparel')
    GROUP BY category
""", conn)

conn.close()

print(segment_data.to_string(index=False))

# Extract numbers
elec  = segment_data[segment_data['category'] == 'electronics'].iloc[0]
appar = segment_data[segment_data['category'] == 'apparel'].iloc[0]

elec_viewers      = int(elec['viewers'])
elec_purchasers   = int(elec['purchasers'])
appar_viewers     = int(appar['viewers'])
appar_purchasers  = int(appar['purchasers'])

elec_rate  = round(elec_purchasers  / elec_viewers  * 100, 2)
appar_rate = round(appar_purchasers / appar_viewers * 100, 2)

print(f"\nElectronics  conversion: {elec_rate}%")
print(f"Apparel      conversion: {appar_rate}%")
print(f"Raw gap:                 {round(elec_rate - appar_rate, 2)}pp")

# ── Section 2 — Z-test ────────────────────────────────────────────────────
print("\n" + "=" * 50)
print("SECTION 2 — TWO-PROPORTION Z-TEST")
print("=" * 50)

print("""
What we are testing:
  Null hypothesis:      electronics and apparel have the same conversion rate
  Alternative:          they are different
  Significance level:   0.05 (5% chance of false positive)
""")

counts = [elec_purchasers, appar_purchasers]
nobs   = [elec_viewers,    appar_viewers]

stat, pvalue = proportions_ztest(counts, nobs)

print(f"Z-statistic: {round(stat, 4)}")
print(f"P-value:     {round(pvalue, 6)}")

if pvalue < 0.05:
    print(f"\nResult: SIGNIFICANT — p={round(pvalue,6)} < 0.05")
    print("We reject the null hypothesis.")
    print("The conversion gap is real, not random chance.")
else:
    print(f"\nResult: NOT SIGNIFICANT — p={round(pvalue,6)} >= 0.05")
    print("We cannot reject the null hypothesis.")

# ── Section 3 — Confidence Interval ──────────────────────────────────────
print("\n" + "=" * 50)
print("SECTION 3 — 95% CONFIDENCE INTERVAL")
print("=" * 50)

print("""
What this tells us:
  The p-value says the gap is real.
  The CI tells us how big the gap is and how precisely we measured it.
""")

elec_low,  elec_high  = proportion_confint(elec_purchasers,  elec_viewers,  alpha=0.05)
appar_low, appar_high = proportion_confint(appar_purchasers, appar_viewers, alpha=0.05)

elec_low_pct   = round(elec_low   * 100, 2)
elec_high_pct  = round(elec_high  * 100, 2)
appar_low_pct  = round(appar_low  * 100, 2)
appar_high_pct = round(appar_high * 100, 2)

gap_low  = round(elec_low_pct  - appar_high_pct, 2)
gap_high = round(elec_high_pct - appar_low_pct,  2)

print(f"Electronics  95% CI: [{elec_low_pct}%, {elec_high_pct}%]")
print(f"Apparel      95% CI: [{appar_low_pct}%, {appar_high_pct}%]")
print(f"\nGap 95% CI:          [{gap_low}pp, {gap_high}pp]")
print(f"\nInterpretation:")
print(f"  We are 95% sure the true conversion gap between")
print(f"  electronics and apparel is between {gap_low}pp and {gap_high}pp.")

# ── Section 4 — Power Analysis ────────────────────────────────────────────
print("\n" + "=" * 50)
print("SECTION 4 — RETROACTIVE POWER ANALYSIS")
print("=" * 50)

print("""
What this tells us:
  Did we have enough users to reliably detect a 1pp lift?
  This proves the test was properly designed — senior DS thinking.
""")

baseline_rate = appar_rate / 100
lift          = 0.01
effect_size   = lift / (baseline_rate * (1 - baseline_rate)) ** 0.5

analysis      = NormalIndPower()
sample_needed = analysis.solve_power(
    effect_size = effect_size,
    power       = 0.8,
    alpha       = 0.05,
    alternative = 'two-sided'
)

sample_needed = int(round(sample_needed))

print(f"Baseline rate (apparel): {appar_rate}%")
print(f"Minimum detectable lift: 1pp")
print(f"Required power:          80%")
print(f"Significance level:      0.05")
print(f"\nSample size needed per segment: {sample_needed:,} users")
print(f"Apparel viewers we have:        {appar_viewers:,} users")
print(f"Electronics viewers we have:    {elec_viewers:,} users")

if appar_viewers >= sample_needed:
    print(f"\nResult: ADEQUATELY POWERED")
    print(f"We had enough users to detect a 1pp lift at 80% power.")
else:
    print(f"\nResult: UNDERPOWERED for 1pp detection")
    print(f"We needed {sample_needed:,} but only had {appar_viewers:,} apparel viewers.")

print("\n" + "=" * 50)
print("SUMMARY — RESUME BULLET NUMBERS")
print("=" * 50)
print(f"  Electronics conversion:  {elec_rate}%")
print(f"  Apparel conversion:      {appar_rate}%")
print(f"  Gap:                     {round(elec_rate - appar_rate, 2)}pp")
print(f"  Z-test p-value:          {round(pvalue, 6)}")
print(f"  95% CI on gap:           [{gap_low}pp, {gap_high}pp]")
print(f"  Sample needed (1pp):     {sample_needed:,} users")
print(f"\nStats validation complete.")