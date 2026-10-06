import sqlite3
conn = sqlite3.connect(r'D:\anonym\war-log\hunt\leads.db')
c = conn.cursor()

# Voice/clinic leads with columns
c.execute("PRAGMA table_info(leads)")
print("Columns:", [row[1] for row in c.fetchall()])

c.execute("SELECT org, email, phone, source_url FROM leads WHERE org LIKE '%voice%' OR org LIKE '%reception%' OR org LIKE '%clinic%' OR org LIKE '%call%' OR org LIKE '%ivr%' OR org LIKE '%callcenter%' OR org LIKE '%contact%' OR org LIKE '%support%' OR org LIKE '%helpdesk%' LIMIT 20")
for row in c.fetchall():
    print(row)

# AI training leads sample
c.execute("SELECT org, email, phone, source_url FROM leads WHERE org LIKE '%scale%' OR org LIKE '%invisible%' OR org LIKE '%turing%' OR org LIKE '%outlier%' OR org LIKE '%mercor%' LIMIT 10")
print("\nAI training sample:")
for row in c.fetchall():
    print(row)
EOF