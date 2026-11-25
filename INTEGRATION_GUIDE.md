# ANANTH — Member 2 Backend Integration Guide

**Track 03 – The Trust Layer | UNCLONE by Detectif.ai**  
**Module Owner**: Member 3 (Audio Intelligence, Adaptive Trust Engine, Recovery & Testing)

---

## 1. Quick Start & Dependencies

Member 3's module is completely self-contained, lightweight, and tested on **Python 3.13.5 and 3.13.7**. It has zero external API dependencies or heavy ML weights.

### Required Dependencies (Pre-installed in `.venv`):
```text
numpy>=2.0.0
scipy>=1.14.0
soundfile>=0.12.1
pytest>=8.0.0
```

Install via requirements file if setting up a fresh environment:
```powershell
pip install -r requirements-member3.txt
```

---

## 2. Public Imports

Member 2 only needs to import from `src.pipeline` and `src.schemas`:

```python
from src.pipeline import AnanthPipeline
from src.schemas import (
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    ActionRiskLevel,
    EvidenceStatus,
)
```

---

## 3. Two-Stage Integration Architecture

To conserve credits and prevent unnecessary external API roundtrips, Member 3 provides a **Two-Stage Architecture**:

```text
Incoming Caller Audio
        │
        ▼
[Stage A: Audio Pre-Flight Check]
  pipeline.stage_a_assess_audio(audio)
        │
        ├── Is audio unsuitable or degraded?
        │     └── YES ──> Return immediate RETRY_AUDIO prompt to user. (Stop; call 0 external APIs)
        └── NO  ──> Proceed
                    │
                    ▼
          Member 2 calls Aletheia & Eidos APIs
                    │
                    ▼
          [Stage B: Trust & Multi-Turn Recovery]
            pipeline.stage_b_evaluate_and_recover(...)
                    │
                    ▼
          Return Unified JSON response to Member 1 (Frontend)
```

---

## 4. Complete Backend Route Example

Here is an example FastAPI / Flask route implementation for Member 2:

```python
from fastapi import FastAPI, UploadFile, File, Form, Depends
from src.pipeline import AnanthPipeline
from src.schemas import (
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    ActionRiskLevel,
    EvidenceStatus,
)

app = FastAPI()

# Instantiate pipeline once during backend application startup
pipeline = AnanthPipeline(production_mode=True)

@app.post("/api/v1/voice-authenticate")
async def authenticate_caller(
    session_id: str = Form(...),
    caller_id: str = Form(...),
    action_risk: str = Form("MEDIUM"),
    audio_file: UploadFile = File(...),
):
    audio_bytes = await audio_file.read()
    risk_tier = ActionRiskLevel(action_risk.upper())

    # =========================================================================
    # STAGE A: Audio Pre-flight Assessment (Physical Acoustic Validation)
    # =========================================================================
    stage_a = pipeline.stage_a_assess_audio(audio_bytes)

    if not stage_a["suitable_for_authentication"]:
        # Do NOT call Aletheia or Eidos; immediately request acoustic retry
        stage_b_retry = pipeline.stage_b_evaluate_and_recover(
            session_id=session_id,
            caller_id=caller_id,
            audio_report=stage_a["raw_report"],
            action_risk_level=risk_tier,
        )
        return stage_b_retry

    # =========================================================================
    # UPSTREAM PROVIDER CALLS: Member 2 queries Aletheia and Eidos APIs
    # =========================================================================
    # (Member 2 maps raw provider responses into Normalized evidence)
    try:
        # aletheia_res = await call_aletheia_api(audio_bytes)
        aletheia_evidence = NormalizedAletheiaEvidence(
            liveness_score=0.95,     # Map from Aletheia response
            confidence=0.92,         # Map from Aletheia response
            session_id=session_id,
            is_mock=False,
        )
    except Exception:
        aletheia_evidence = NormalizedAletheiaEvidence(
            status=EvidenceStatus.UNAVAILABLE,
            session_id=session_id,
        )

    try:
        # eidos_res = await call_eidos_api(audio_bytes, caller_id)
        eidos_evidence = NormalizedEidosEvidence(
            match_score=0.92,        # Map from Eidos response
            confidence=0.90,         # Map from Eidos response
            session_id=session_id,
            is_mock=False,
        )
    except Exception:
        eidos_evidence = NormalizedEidosEvidence(
            status=EvidenceStatus.UNAVAILABLE,
            session_id=session_id,
        )

    # =========================================================================
    # STAGE B: Adaptive Trust Evaluation & State Machine Transition
    # =========================================================================
    final_response = pipeline.stage_b_evaluate_and_recover(
        session_id=session_id,
        caller_id=caller_id,
        audio_report=stage_a["raw_report"],
        aletheia_evidence=aletheia_evidence,
        eidos_evidence=eidos_evidence,
        action_risk_level=risk_tier,
        is_mock=False,
    )

    # Return unified JSON payload directly to Member 1 (Frontend UI)
    return final_response
```

---

## 5. Provider API Mapping Semantics

When mapping external Detectif.ai API responses to Member 3 schemas, Member 2 should follow these guidelines:

### Aletheia Mapping (`NormalizedAletheiaEvidence`):
- `liveness_score` (`float` between `0.0` and `1.0`):
  - `1.0` indicates verified genuine human biological speech.
  - $\le 0.35$ indicates credible synthetic deepfake or voice cloning attack.
- `confidence` (`float` between `0.0` and `1.0`):
  - Model confidence or prediction certainty.
- If the endpoint fails or times out: set `status = EvidenceStatus.UNAVAILABLE`.

### Eidos Mapping (`NormalizedEidosEvidence`):
- `match_score` (`float` between `0.0` and `1.0`):
  - `1.0` indicates strong acoustic similarity to enrolled customer voiceprint.
  - $\le 0.40$ indicates speaker identity mismatch (impersonator using real human voice).
- `confidence` (`float` between `0.0` and `1.0`):
  - Speaker recognition model confidence.
- If customer profile not found: set `enrolled_profile_found = False`.

*Note*: If actual Detectif provider response fields differ (e.g. `is_spoof: bool`), Member 2 can convert them to a unit interval score: `liveness_score = 0.05 if is_spoof else 0.95`.

---

## 6. Frontend JSON Contract (for Member 1)

Every response produced by `stage_b_evaluate_and_recover()` follows this JSON structure:

```json
{
  "session_id": "sess_89102",
  "caller_id": "user_4401",
  "attempt_number": 1,
  "verification_status": "VERIFIED",
  "decision": "ALLOW",
  "audio_quality": "GOOD",
  "estimated_speech_duration": 2.5,
  "estimated_snr": 24.2,
  "evidence_summary": {
    "audio_quality_status": "GOOD",
    "snr_db": 24.2,
    "speech_duration_s": 2.5,
    "clipping_pct": 0.0,
    "aletheia_status": "VALID",
    "aletheia_liveness_score": 0.95,
    "aletheia_confidence": 0.92,
    "eidos_status": "VALID",
    "eidos_match_score": 0.94,
    "eidos_confidence": 0.9
  },
  "conflicting_evidence": false,
  "reason_codes": [
    "VOICE_AND_IDENTITY_VERIFIED"
  ],
  "recovery_action": "VERIFICATION_COMPLETE",
  "customer_message": "Voice authentication successful.",
  "retries_remaining": 3,
  "service_retries_remaining": 2,
  "session_state": "VOICE_VERIFIED",
  "sensitive_operations_paused": false,
  "independent_auth_required": false,
  "terminal_state": true,
  "processing_time_ms": 1.25,
  "demo_mode": false,
  "security_restrictions": []
}
```

---

## 7. Security Restrictions & Invariants

1. **Backend Controls Risk & Authorization**:
   - Never trust frontend-supplied flags such as `is_verified: true` or `retry_count`. All state counters and decisions are enforced server-side by `AnanthPipeline`.
2. **Financial Operations Mandatory Step-Up**:
   - For `ActionRiskLevel.FINANCIAL`, voice verification alone **never** authorizes fund movement; the pipeline always returns `STEP_UP_CHALLENGE` with `independent_auth_required = true`.
3. **Permanent Lockout for Suspicious Sessions**:
   - Once a session detects a deepfake (`SUSPICIOUS` / `DENY`), it is locked in state `BLOCKED`. Subsequent audio submissions will remain blocked.
