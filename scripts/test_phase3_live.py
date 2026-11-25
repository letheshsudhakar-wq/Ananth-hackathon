"""Live Phase 3 endpoint checks against a running backend (no mocks)."""
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://127.0.0.1:8000"
GOOD_AUDIO = {
    "valid": True, "quality_status": "GOOD", "suitable_for_authentication": True,
    "duration_seconds": 3.2, "estimated_speech_duration_seconds": 2.6,
    "sample_rate": 16000, "channel_count": 1, "estimated_noise_level_dbfs": -55.0,
    "estimated_snr_db": 26.0, "silence_percentage": 12.0, "clipping_percentage": 0.0,
    "rms_dbfs": -20.0, "peak_amplitude": 0.62, "detected_issues": [],
    "recommended_action": "PROCEED", "quality_notes": ["clear"],
}
REGIONAL = {"regional_language": {"status": "PASS", "findings": {"preferred_recovery_language": "en"}, "measurements": {}}}


def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST" if data else "GET")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body, round((time.perf_counter() - started) * 1000, 2)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}"), round((time.perf_counter() - started) * 1000, 2)


def main():
    ok = True
    status, cfg, ms = call("/v1/n8n/config")
    print(f"config: http={status} gemini={cfg.get('gemini')} detectif={cfg.get('detectif')} {ms}ms")
    ok = ok and status == 200

    base = {
        "caller_id": "live_caller", "action_risk": "LOW", "audio_report": GOOD_AUDIO,
        "preferred_language": "en", "agent_findings": REGIONAL, "use_gemini": False,
    }
    scenarios = [
        ("verified", {"aletheia": {"liveness_score": 0.95, "confidence": 0.91}, "eidos": {"match_score": 0.94, "confidence": 0.88}}, "VERIFIED"),
        ("missing_evidence", {"aletheia": None, "eidos": None}, "RECOVERY_REQUIRED"),
        ("deepfake", {"aletheia": {"liveness_score": 0.05, "confidence": 0.95}, "eidos": {"match_score": 0.96, "confidence": 0.95}}, "BLOCKED"),
    ]
    for name, evidence, expected in scenarios:
        payload = {**base, "session_id": f"live_{name}_{uuid.uuid4().hex[:6]}", **evidence}
        status, body, ms = call("/v1/n8n/trust", payload)
        outcome = body.get("outcome")
        print(f"trust/{name}: http={status} outcome={outcome} action={body.get('recovery_action')} {ms}ms")
        ok = ok and status == 200 and outcome == expected

    payload = {
        "session_id": f"live_orch_{uuid.uuid4().hex[:6]}", "caller_id": "live_caller", "action_risk": "LOW",
        "audio_report": GOOD_AUDIO, "preferred_language": "en",
        "aletheia": {"liveness_score": 0.95, "confidence": 0.91},
        "eidos": {"match_score": 0.94, "confidence": 0.88}, "use_gemini": False,
    }
    status, body, ms = call("/v1/n8n/orchestrate", payload)
    required = {"session_id", "activated_agents", "agent_findings", "detection_result", "identity_result",
                "trust_decision", "decision_reasons", "recovery_action", "customer_message",
                "preferred_language", "processing_time_ms", "errors", "simulation_mode"}
    missing = required - set(body.keys())
    print(f"orchestrate: http={status} outcome={body.get('outcome')} missing={sorted(missing)} {ms}ms")
    ok = ok and status == 200 and not missing and body.get("outcome") == "VERIFIED"

    status, body, ms = call("/v1/n8n/recovery", {
        "session_id": f"live_rec_{uuid.uuid4().hex[:6]}",
        "verification_status": "ADDITIONAL_VERIFICATION_REQUIRED", "decision": "RETRY_AUDIO",
        "session_state": "RETRY_AUDIO", "reason_codes": ["POOR_AUDIO_QUALITY"],
        "recovery_action": "REQUEST_LONGER_RECORDING", "preferred_language": "ta", "use_gemini": True,
    })
    print(f"recovery: http={status} action={body.get('recovery_action')} lang={body.get('preferred_language')} {ms}ms")
    ok = ok and status == 200 and body.get("recovery_action") == "COLLECT_MORE_SPEECH"

    print("PHASE 3 LIVE TESTS:", "ALL OK" if ok else "ISSUES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
