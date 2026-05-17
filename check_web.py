import sqlite3
import json

conn = sqlite3.connect('data/synapse.db')
c = conn.cursor()
c.execute('SELECT id, topic, web_context FROM sequential_debates ORDER BY created_at DESC LIMIT 1')
row = c.fetchone()

if row:
    print(f"Debate: {row[0]}")
    print(f"Topic: {row[1][:80]}...")
    print(f"Has web_context: {row[2] is not None}")
    
    if row[2]:
        ctx = json.loads(row[2])
        print(f"Searches: {len(ctx.get('searches', []))}")
        for s in ctx.get('searches', []):
            status = "OK" if s.get('success') else f"FAIL: {s.get('error', '')[:50]}"
            print(f"  - {s['site_label']}: {status}")
else:
    print("No debates found")

conn.close()
