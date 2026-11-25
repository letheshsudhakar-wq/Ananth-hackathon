"""Fire webhooks at the LIVE n8n server for the 5 agent workflows (validates the n8n side)."""
import glob
import json
import os
import urllib.request
import urllib.error

N8N_WEBHOOK = "http://localhost:5678/webhook"
SCHEMA_KEYS = {"agent_name", "session_id", "status", "findings", "measurements", "confidence",
               "limitations", "recommended_action", "processing_time_ms", "error"}

PAYLOADS = {
    "agent_speech_sufficiency.json": {"session_id": "n8n_live_ss", "sample_rate": 16000, "min_speech_seconds": 1.8},
    "agent_acoustic_intelligence.json": {"session_id": "n8n_live_ac"},
    "agent_network_resilience.json": {"session_id": "n8n_live_net", "webrtc_stats": {"packet_loss_rate": 0.02}},
    "agent_regional_language.json": {"session_id": "n8n_live_rl", "detected_language": "gu"},
    "agent_cross_language_identity.json": {
        "session_id": "n8n_live_xl", "enrolled_language": "hi", "current_language": "en", "eidos_match_score": 0.79
    },
}


def api_call(url, data):
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")
    except Exception as exc:
        return None, str(exc)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ok = True
    for f in sorted(glob.glob(os.path.join(root, "n8n", "workflows", "agent_*.json"))):
        name = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            wf = json.load(fh)
        hook_path = wf["nodes"][0]["parameters"]["path"]
        s, body = api_call(f"{N8N_WEBHOOK}/{hook_path}", json.dumps(PAYLOADS.get(name, {})).encode())
        schema_ok = isinstance(body, dict) and SCHEMA_KEYS.issubset(body.keys())
        print(f"{name}: webhook={s} schema_ok={schema_ok} agent={body.get('agent_name') if isinstance(body, dict) else None}")
        ok = ok and schema_ok
    print("N8N WEBHOOK PATH TESTS:", "ALL OK" if ok else "ISSUES")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
