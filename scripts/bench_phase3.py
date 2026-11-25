"""Benchmark Phase 3 orchestration on a real WAV file (synthetic signal, acoustic only)."""
import json
import os
import sys
import time
import urllib.request
import uuid

import numpy as np
import soundfile as sf

BASE = "http://127.0.0.1:8000"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(ROOT, "backend", "data", "agent_sessions")
os.makedirs(AUDIO_DIR, exist_ok=True)

SR = 16000
rng = np.random.RandomState(7)
t = np.arange(int(SR * 3.2)) / SR
sig = sum(np.sin(2 * np.pi * 180 * h * t) / h for h in range(1, 6)) + 0.05 * rng.randn(len(t))
env = ((t % 1.0) < 0.8).astype(np.float32)
audio = (0.25 * sig * env).astype(np.float32)
path = os.path.join(AUDIO_DIR, f"bench_{uuid.uuid4().hex[:8]}.wav")
sf.write(path, audio, SR)


def post(endpoint, payload):
    req = urllib.request.Request(
        BASE + endpoint,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
    return body, round((time.perf_counter() - started) * 1000, 2)


def main():
    session_id = f"bench_{uuid.uuid4().hex[:8]}"
    payload = {
        "session_id": session_id,
        "caller_id": "bench",
        "action_risk": "LOW",
        "audio_path": path,
        "preferred_language": "en",
        "enrolled_language": "en",
        "current_language": "en",
        "eidos": {"match_score": 0.9, "confidence": 0.9},
    }
    body, ms = post("/v1/n8n/agents/batch", payload)
    agent_sum = sum(v.get("processing_time_ms", 0) for v in body.get("agent_findings", {}).values())
    print(f"batch first: {ms}ms agents={body.get('activated_agents')} sum_agent_ms={agent_sum:.1f}")
    body2, ms2 = post("/v1/n8n/agents/batch", payload)
    agent_sum2 = sum(v.get("processing_time_ms", 0) for v in body2.get("agent_findings", {}).values())
    print(f"batch cached: {ms2}ms agents={body2.get('activated_agents')} sum_agent_ms={agent_sum2:.1f}")

    orch_payload = {**payload, "session_id": f"bench_orch_{uuid.uuid4().hex[:8]}", "use_gemini": False}
    orch, orch_ms = post("/v1/n8n/orchestrate", orch_payload)
    print(f"orchestrate: {orch_ms}ms outcome={orch.get('outcome')} agents={len(orch.get('activated_agents', []))} "
          f"audio_quality={orch.get('audio_quality', {}).get('quality_status')} errors={orch.get('errors')}")
    print(f"orchestrator_reported_ms={orch.get('processing_time_ms')} agent_processing_ms={orch.get('agent_processing_time_ms')}")
    print("PERFORMANCE SCRIPT: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
