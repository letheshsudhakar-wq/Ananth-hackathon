"""Create an API key row directly in the n8n SQLite DB and test it against /api/v1/workflows."""
import sqlite3
import uuid
import urllib.request
import urllib.error
import json
import datetime

DB = r"C:\Users\lethe\.n8n\database.sqlite"
API = "http://localhost:5678/api/v1/workflows"
KEY = "an8nphase2testkey_" + uuid.uuid4().hex[:24]

con = sqlite3.connect(DB)
cur = con.cursor()
now = datetime.datetime.utcnow().isoformat()
cur.execute(
    "INSERT INTO user_api_keys (id, userId, label, apiKey, createdAt, updatedAt, scopes, audience, lastUsedAt) "
    "VALUES (?, (SELECT id FROM user WHERE roleSlug='global:owner' LIMIT 1), ?, ?, ?, ?, ?, ?, ?)",
    (str(uuid.uuid4()), "phase2-api-key", KEY, now, now, "[]", "[]", None),
)
con.commit()
print("inserted key:", KEY)

for header_name, value in [("X-N8N-API-KEY", KEY), ("Authorization", "Bearer " + KEY)]:
    req = urllib.request.Request(API, method="GET", headers={header_name: value})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            print(f"{header_name}: {resp.status} -> {resp.read()[:120]}")
    except urllib.error.HTTPError as exc:
        print(f"{header_name}: {exc.code}")
