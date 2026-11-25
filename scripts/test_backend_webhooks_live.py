"""
Live backend webhook tests for Phase 2 agent endpoints (the same calls n8n
HTTP Request nodes make from the imported agent workflows).

Verifies the n8n -> backend contract end-to-end against the running backend.
"""
import json
import os
import sys
import urllib.request
import urllib.error

BACKEND = "http://localhost:8000"
SCHEMA_KEYS = {
    "agent_name", "session_id", "status", "findings", "measurements",
    "confidence", "limitations", "recommended_action", "processing_time_ms", "error",
}

REQUESTS = [
    ("/v1/agents/speech_sufficiency", {"session_id": "live_web_ss", "sample_rate": 16000}),
    ("/v1/agents/acoustic_intelligence", {"session_id": "live_web_ac"}),
    ("/v1/agents/network_resilience", {"session_id": "live_web_net", "webrtc_stats": {"packet_loss_rate": 0.02}}),
    ("/v1/agents/regional_language", {"session_id": "live_web_rl", "detected_language": "kn", "confidence": 0.9}),
    ("/v1/agents/cross_language_identity", {
        "session_id": "live_web_xl", "enrolled_language": "en", "current_language": "hi",
        "eidos_match_score": 0.8,
    }),
]


def api_call(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def main():
    ok = True
    s0, _ = api_call("GET", BACKEND + "/v1/n8n/health")
    print("backend health:", s0)
    ok = ok and s0 == 200
    for path, payload in REQUESTS:
        s, body = api_call("POST", BACKEND + path, data=json.dumps(payload).encode(),
                           headers={"Content-Type": "application/json"})
        schema_ok = isinstance(body, dict) and SCHEMA_KEYS.issubset(body.keys())
        status_val = body.get("status") if isinstance(body, dict) else None
        agent = body.get("agent_name") if isinstance(body, dict) else None
        print(f"{path}: http={s} agent={agent} status={status_val} schema_ok={schema_ok}")
        ok = ok and s == 200 and schema_ok
    print("BACKEND WEBHOOK TESTS:", "ALL OK" if ok else "ISSUES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
