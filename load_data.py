import sqlite3
import pandas as pd
import zipfile
import os

ZIP_PATH = "data/ecommerce-behavior-data-from-multi-category-store.zip"
DB_PATH = "data/ecommerce.db"
CHUNK_SIZE = 300_000

# Step 1 — See what's inside the zip
print("Files in zip:")
with zipfile.ZipFile(ZIP_PATH, 'r') as z:
    files = z.namelist()
    for f in files:
        print(f" -", f)

# Step 2 — Pick the October file only
october_file = [f for f in files if 'Oct' in f][0]
print(f"\nLoading: {october_file}")

# Step 3 — Load into SQLite in chunks
print("\nStarting chunked load into SQLite...")
conn = sqlite3.connect(DB_PATH)

chunk_num = 0
with zipfile.ZipFile(ZIP_PATH, 'r') as z:
    with z.open(october_file) as csv_file:
        for chunk in pd.read_csv(csv_file, chunksize=CHUNK_SIZE):
            chunk.to_sql(
                'events',
                conn,
                if_exists='append' if chunk_num > 0 else 'replace',
                index=False
            )
            chunk_num += 1
            print(f" Chunk {chunk_num} loaded — {chunk_num * CHUNK_SIZE:,} rows so far")

print(f"\nDone. Total chunks: {chunk_num}")

# Step 4 — Verify the load
print("\n--- Verification ---")

print("\nEvent type distribution:")
result = pd.read_sql("""
    SELECT 
        event_type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct
    FROM events
    GROUP BY event_type
""", conn)
print(result.to_string(index=False))

print("\nDate range:")
result = pd.read_sql("""
    SELECT 
        MIN(event_time) as earliest,
        MAX(event_time) as latest
    FROM events
""", conn)
print(result.to_string(index=False))

print("\nUnique counts:")
result = pd.read_sql("""
    SELECT
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(DISTINCT user_session) as unique_sessions,
        COUNT(DISTINCT product_id) as unique_products
    FROM events
""", conn)
print(result.to_string(index=False))

print("\nNull rates:")
result = pd.read_sql("""
    SELECT
        ROUND(SUM(CASE WHEN category_code IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as category_code_null_pct,
        ROUND(SUM(CASE WHEN brand IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as brand_null_pct
    FROM events
""", conn)
print(result.to_string(index=False))

conn.close()
print("\nDay 1 complete. Database ready at data/ecommerce.db")