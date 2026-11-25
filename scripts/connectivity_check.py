"""Connectivity check for backend (:8000) and n8n (:5678)."""
import json
import urllib.request


def fetch(url: str, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except Exception as exc:
        return None, str(exc)


if __name__ == "__main__":
    s, b = fetch("http://localhost:5678/healthz")
    print("n8n /healthz:", s, b)
    s, b = fetch("http://localhost:8000/v1/n8n/health")
    print("backend /v1/n8n/health:", s, b)
    s, b = fetch(
        "http://localhost:8000/v1/agents/regional_language",
        data=json.dumps({"session_id": "conn_check_1", "detected_language": "hi"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    print("backend POST /v1/agents/regional_language:", s, b.get("agent_name") if isinstance(b, dict) else b)
