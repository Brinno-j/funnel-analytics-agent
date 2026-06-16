import sqlite3
import pandas as pd
from statsmodels.stats.proportion import proportions_ztest, proportion_confint
from statsmodels.stats.power import NormalIndPower
from google import genai
from dotenv import load_dotenv
import os
import re

load_dotenv()

DB_PATH = "data/ecommerce.db"
client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

# ── Tool 1 — Run SQL ──────────────────────────────────────────────────────
def run_sql(query: str) -> str:
    """Execute a SQL query and return results as a string."""
    
    # Guardrails — block destructive operations
    blocked = ['DELETE', 'DROP', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']
    query_upper = query.upper()
    for word in blocked:
        if word in query_upper:
            return f"BLOCKED: '{word}' operations are not permitted."

    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(query, conn)
        conn.close()
        if df.empty:
            return "Query returned no results."
        return df.to_string(index=False)
    except Exception as e:
        return f"SQL ERROR: {str(e)}"


# ── Tool 2 — Run Z-test ───────────────────────────────────────────────────
def run_ztest(category_a: str, category_b: str) -> str:
    """
    Run a two-proportion z-test comparing conversion rates
    between two product categories.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
            SELECT
                SUBSTR(category_code, 1, INSTR(category_code, '.') - 1) AS category,
                COUNT(DISTINCT CASE WHEN event_type = 'view'     THEN user_id END) AS viewers,
                COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS purchasers
            FROM events
            WHERE category_code IS NOT NULL
            AND SUBSTR(category_code, 1, INSTR(category_code, '.') - 1) IN (?, ?)
            GROUP BY category
        """
        df = pd.read_sql(query, conn, params=[category_a, category_b])
        conn.close()

        if len(df) < 2:
            return f"Could not find data for both categories: {category_a}, {category_b}"

        a = df[df['category'] == category_a].iloc[0]
        b = df[df['category'] == category_b].iloc[0]

        rate_a = round(a['purchasers'] / a['viewers'] * 100, 2)
        rate_b = round(b['purchasers'] / b['viewers'] * 100, 2)

        counts = [int(a['purchasers']), int(b['purchasers'])]
        nobs   = [int(a['viewers']),    int(b['viewers'])]

        stat, pvalue = proportions_ztest(counts, nobs)

        a_low, a_high = proportion_confint(int(a['purchasers']), int(a['viewers']), alpha=0.05)
        b_low, b_high = proportion_confint(int(b['purchasers']), int(b['viewers']), alpha=0.05)

        gap      = round(rate_a - rate_b, 2)
        gap_low  = round(a_low  * 100 - b_high * 100, 2)
        gap_high = round(a_high * 100 - b_low  * 100, 2)

        # Power analysis
        baseline     = rate_b / 100
        effect_size  = 0.01 / (baseline * (1 - baseline)) ** 0.5
        analysis     = NormalIndPower()
        sample_needed = int(round(analysis.solve_power(
            effect_size=effect_size, power=0.8, alpha=0.05, alternative='two-sided'
        )))

        pvalue_str = "< 0.0001" if pvalue < 0.0001 else round(pvalue, 6)

        result = f"""
Z-TEST RESULTS: {category_a} vs {category_b}
{'─' * 45}
{category_a} conversion:  {rate_a}%  ({int(a['purchasers']):,} / {int(a['viewers']):,} users)
{category_b} conversion:  {rate_b}%  ({int(b['purchasers']):,} / {int(b['viewers']):,} users)

Gap:                {gap}pp
P-value:            {pvalue_str}
95% CI on gap:      [{gap_low}pp, {gap_high}pp]
Significant:        {'YES — gap is real, not random noise' if pvalue < 0.05 else 'NO — gap could be random'}

Power analysis:
  Sample needed to detect 1pp lift (80% power): {sample_needed:,} users
  {category_b} viewers available: {int(b['viewers']):,}
  Test status: {'Adequately powered' if int(b['viewers']) >= sample_needed else 'Underpowered'}
"""
        return result

    except Exception as e:
        return f"Z-TEST ERROR: {str(e)}"


# ── Agent — NL question → SQL → answer ───────────────────────────────────
def ask_agent(question: str) -> str:
    """
    Takes a natural language question, uses Gemini to generate SQL,
    executes it, then generates a plain English answer.
    """

    print(f"\n{'=' * 55}")
    print(f"QUESTION: {question}")
    print(f"{'=' * 55}")

    # ── Step 1 — Generate SQL ─────────────────────────────────────────
    sql_prompt = f"""
You are a data analyst working with an e-commerce SQLite database.

Table: events
Columns:
  - event_time    (timestamp)
  - event_type    (string: 'view', 'cart', 'purchase')
  - product_id    (integer)
  - category_id   (integer)
  - category_code (string, e.g. 'electronics.smartphone') — 32% NULL
  - brand         (string) — 14% NULL
  - price         (float)
  - user_id       (integer)
  - user_session  (string)

Rules:
  - Always use COUNT(DISTINCT user_id) for funnel metrics — not COUNT(*)
  - Extract top-level category with: SUBSTR(category_code, 1, INSTR(category_code, '.') - 1)
  - Filter WHERE category_code IS NOT NULL when grouping by category
  - Never use DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE
  - Return ONLY the SQL query, no explanation, no markdown, no backticks

Question: {question}

SQL:"""

    sql_response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=sql_prompt
    )

    sql_query = sql_response.text.strip()
    sql_query = re.sub(r'```sql|```', '', sql_query).strip()

    print(f"\nGENERATED SQL:")
    print(sql_query)

    # ── Step 2 — Execute SQL ──────────────────────────────────────────
    sql_result = run_sql(sql_query)
    print(f"\nSQL RESULT:")
    print(sql_result)

    # ── Step 3 — Generate answer ──────────────────────────────────────
    answer_prompt = f"""
You are a senior data scientist presenting findings to a product manager.

Question asked: {question}

SQL query used:
{sql_query}

Query result:
{sql_result}

Write a clear, concise answer in 3-5 sentences.
- Lead with the direct answer to the question
- Include the specific numbers from the result
- End with one actionable business implication
- Do not mention SQL or technical details
"""

    answer_response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=answer_prompt
    )

    answer = answer_response.text.strip()
    print(f"\nANSWER:")
    print(answer)

    return answer


# ── Main — Test with 5 questions ─────────────────────────────────────────
if __name__ == "__main__":

    print("FUNNEL ANALYTICS AGENT")
    print("=" * 55)
    print("Powered by Gemini 3.5 Flash + SQLite")
    print("=" * 55)

    # Question 1 — Overall funnel
    ask_agent("What is the overall view to purchase conversion rate?")

    # Question 2 — Category breakdown
    ask_agent("Which product category has the lowest conversion rate?")

    # Question 3 — Statistical validation
    print(f"\n{'=' * 55}")
    print("QUESTION: Is the gap between electronics and apparel statistically significant?")
    print(f"{'=' * 55}")
    print(run_ztest("electronics", "apparel"))

    # Question 4 — Brand analysis
    ask_agent("What are the top 5 brands by number of purchases?")

    # Question 5 — Guardrail test
    print(f"\n{'=' * 55}")
    print("QUESTION: Guardrail test — attempt DELETE")
    print(f"{'=' * 55}")
    print(run_sql("DELETE FROM events WHERE event_type = 'view'"))