"""Inspect n8n sqlite DB for users / API keys (dev utility)."""
import sqlite3

con = sqlite3.connect(r"C:\Users\lethe\.n8n\database.sqlite")
cur = con.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("tables:", tables)
for t in tables:
    if any(k in t.lower() for k in ("user", "api", "key")):
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
        rows = cur.execute(f"SELECT * FROM {t} LIMIT 5").fetchall()
        print(t, cols)
        for r in rows:
            print("  ", r)
