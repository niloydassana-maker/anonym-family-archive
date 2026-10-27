import sqlite3
import json

conn = sqlite3.connect('scratch/icu_pipeline.db')
cursor = conn.cursor()

print("--- RECENT DISPATCHES / STATUSES ---")
rows = cursor.execute("""
    SELECT repo, issue_number, status, title, corridor, reason 
    FROM deliveries 
    ORDER BY rowid DESC 
    LIMIT 30
""").fetchall()

for r in rows:
    print(f"[{r[2]}] {r[0]}#{r[1]} | Title: {r[3]} | Corridor: {r[4]}")
    if "REJECTED" in r[2] or "DISPATCHED" in r[2]:
        print(f"   Reason: {r[5][:120] if r[5] else 'None'}")
