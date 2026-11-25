"""
Live test for Phase 2 n8n workflows:
1. Import each agent workflow into a running n8n instance (REST API).
2. Activate it.
3. Fire the webhook with a JSON payload.
4. Verify the webhook response contains the StandardAgentResponse schema keys.
"""
import glob
import json
import os
import urllib.request
import urllib.error

N8N_API = "http://localhost:5678/api/v1/workflows"
WEBHOOK_BASE = "http://localhost:5678/webhook"

PAYLOADS = {
    "agent_speech_sufficiency.json": {"session_id": "live_ss", "sample_rate": 16000, "min_speech_seconds": 1.8},
    "agent_acoustic_intelligence.json": {"session_id": "live_ac"},
    "agent_network_resilience.json": {"session_id": "live_net", "webrtc_stats": {"packet_loss_rate": 0.02}},
    "agent_regional_language.json": {"session_id": "live_rl", "detected_language": "kn"},
    "agent_cross_language_identity.json": {
        "session_id": "live_xl", "enrolled_language": "en", "current_language": "hi", "eidos_match_score": 0.8
    },
}

SCHEMA_KEYS = {"agent_name", "session_id", "status", "findings", "measurements", "confidence", "limitations",
               "recommended_action", "processing_time_ms", "error"}


def api_call(method: str, url: str, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results = []
    for f in sorted(glob.glob(os.path.join(root, "n8n", "workflows", "agent_*.json"))):
        name = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            wf = json.load(fh)
        # 1. Import
        s, created = api_call("POST", N8N_API, data=json.dumps(wf).encode(),
                              headers={"Content-Type": "application/json"})
        wid = created.get("id") if isinstance(created, dict) else None
        # 2. Activate
        act_status = None
        if wid:
            s2, _ = api_call("POST", f"{N8N_API}/{wid}/activate")
            act_status = s2
        # 3. Fire webhook
        hook_path = wf["nodes"][0]["parameters"]["path"]
        payload = PAYLOADS.get(name, {"session_id": "live_" + name[:8]})
        s3, body = api_call("POST", f"{WEBHOOK_BASE}/{hook_path}",
                            data=json.dumps(payload).encode(),
                            headers={"Content-Type": "application/json"})
        schema_ok = isinstance(body, dict) and SCHEMA_KEYS.issubset(body.keys())
        agent_name = body.get("agent_name") if isinstance(body, dict) else None
        status_val = body.get("status") if isinstance(body, dict) else None
        results.append((name, s, wid is not None, act_status, s3, schema_ok, agent_name, status_val))
        print(f"{name}: import={s} id={wid} activate={act_status} webhook={s3} schema_ok={schema_ok} "
              f"agent={agent_name} status={status_val}")

    all_ok = all(r[5] and r[4] in (200, 201, 202) for r in results)
    print("LIVE N8N TESTS:", "ALL OK" if all_ok else "ISSUES")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
