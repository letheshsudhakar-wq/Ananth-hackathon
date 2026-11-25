"""Inspect n8n sqlite DB: users and API keys."""
import sqlite3

con = sqlite3.connect(r"C:\Users\lethe\.n8n\database.sqlite")
cur = con.cursor()
print("users:")
for r in cur.execute("SELECT id, email, roleSlug, disabled FROM user").fetchall():
    print("  ", r)
print("user_api_keys:")
for r in cur.execute("SELECT id, userId, label, apiKey, scopes, audience FROM user_api_keys").fetchall():
    print("  ", (r[0], r[1], r[2], str(r[3])[:40] + "..." if r[3] else None, r[4], r[5]))
print("workflows:")
for r in cur.execute("SELECT id, name FROM workflow LIMIT 20").fetchall():
    print("  ", r)
