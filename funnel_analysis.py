import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

DB_PATH = "data/ecommerce.db"

conn = sqlite3.connect(DB_PATH)

# ── Section 1 — Overall Funnel ─────────────────────────────────────────────
print("=" * 50)
print("SECTION 1 — OVERALL FUNNEL")
print("=" * 50)

overall_funnel = pd.read_sql("""
    SELECT
        COUNT(DISTINCT CASE WHEN event_type = 'view' THEN user_id END) AS total_viewers,
        COUNT(DISTINCT CASE WHEN event_type = 'cart' THEN user_id END) AS total_cart_adders,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS total_purchasers
    FROM events
""", conn)

print(overall_funnel.to_string(index=False))

viewers = overall_funnel['total_viewers'][0]
cart_adders = overall_funnel['total_cart_adders'][0]
purchasers = overall_funnel['total_purchasers'][0]

view_to_cart     = round(cart_adders  / viewers     * 100, 2)
view_to_purchase = round(purchasers   / viewers     * 100, 2)
cart_to_purchase = round(purchasers   / cart_adders * 100, 2)

print(f"\nView → Cart:     {view_to_cart}%")
print(f"View → Purchase: {view_to_purchase}%")
print(f"Cart → Purchase: {cart_to_purchase}%")
print(f"\nNOTE: Cart→Purchase can exceed 100% because some users")
print(f"purchase via 'buy now' without adding to cart first.")

# ── Section 2 — Funnel by Category ────────────────────────────────────────
print("\n" + "=" * 50)
print("SECTION 2 — FUNNEL BY CATEGORY")
print("=" * 50)

category_funnel = pd.read_sql("""
    SELECT
        SUBSTR(category_code, 1, INSTR(category_code, '.') - 1) AS category,
        COUNT(DISTINCT CASE WHEN event_type = 'view'     THEN user_id END) AS total_viewers,
        COUNT(DISTINCT CASE WHEN event_type = 'cart'     THEN user_id END) AS total_cart_adders,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS total_purchasers
    FROM events
    WHERE category_code IS NOT NULL
    GROUP BY category
    HAVING total_viewers > 10000
    ORDER BY total_viewers DESC
""", conn)

# Compute conversion rates
category_funnel['view_to_cart_pct'] = round(
    category_funnel['total_cart_adders'] / category_funnel['total_viewers'] * 100, 2)
category_funnel['view_to_purchase_pct'] = round(
    category_funnel['total_purchasers'] / category_funnel['total_viewers'] * 100, 2)

print(category_funnel[[
    'category', 'total_viewers', 'total_cart_adders',
    'total_purchasers', 'view_to_cart_pct', 'view_to_purchase_pct'
]].to_string(index=False))

# ── Section 3 — Identify worst and best performing categories ──────────────
print("\n" + "=" * 50)
print("SECTION 3 — BEST AND WORST CATEGORIES (view→purchase)")
print("=" * 50)

site_avg = view_to_purchase
category_funnel['vs_site_avg_pp'] = round(
    category_funnel['view_to_purchase_pct'] - site_avg, 2)

best  = category_funnel.nlargest(3,  'view_to_purchase_pct')[['category', 'view_to_purchase_pct', 'vs_site_avg_pp']]
worst = category_funnel.nsmallest(3, 'view_to_purchase_pct')[['category', 'view_to_purchase_pct', 'vs_site_avg_pp']]

print(f"\nSite average view→purchase: {site_avg}%")
print("\nTop 3 categories:")
print(best.to_string(index=False))
print("\nBottom 3 categories:")
print(worst.to_string(index=False))

# ── Section 4 — Funnel Bar Chart ──────────────────────────────────────────
print("\n" + "=" * 50)
print("SECTION 4 — SAVING FUNNEL CHART")
print("=" * 50)

stages = ['Viewers', 'Cart Adders', 'Purchasers']
values = [viewers, cart_adders, purchasers]

plt.figure(figsize=(8, 5))
bars = plt.bar(stages, values, color=['#4C72B0', '#DD8452', '#55A868'])
plt.title('E-Commerce Funnel — October 2019', fontsize=14)
plt.ylabel('Unique Users')
plt.xlabel('Funnel Stage')

for bar, val in zip(bars, values):
    plt.text(bar.get_x() + bar.get_width() / 2,
             bar.get_height() + 50000,
             f'{val:,}',
             ha='center', fontsize=10)

plt.tight_layout()
plt.savefig('funnel_chart.png', dpi=150)
print("Chart saved as funnel_chart.png")

conn.close()
print("\nFunnel analysis complete.")