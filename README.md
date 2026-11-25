# ANANTH - Member 3: Audio Intelligence & Adaptive Trust Engine

Track: **Track 03 – The Trust Layer | UNCLONE by Detectif.ai**

---

## 1. Overview & Responsibilities

This module constitutes **Member 3's component** of project **ANANTH**. It is designed to sit between raw audio acquisition and final authentication outcome delivery, providing:
1. **Audio Quality Intelligence**: Pre-flight physical signal assessment (Noise, SNR, Voice Duration, Clipping) before biometrics are computed.
2. **Adaptive Trust Engine**: Calibrated decision-making balancing Aletheia (liveness/anti-spoof) and Eidos (speaker verification) evidence.
3. **Adaptive Authentication Recovery**: Safe fallback flows when audio is suboptimal or evidence is conflicting, strictly without weakening security barriers.
4. **Explainable Security Telemetry**: Human-readable, audited rationale behind every allow/deny/challenge decision.

---

## 2. Strict Security Invariant

> **Golden Rule**: Poor audio quality or high background noise must **never** weaken or bypass authentication gates. If an audio sample is degraded or unusable, the system requests a clean retry (`RETRY_AUDIO`) or enforces a step-up challenge (`STEP_UP_CHALLENGE`). Under no circumstances is a low-quality sample accepted with reduced thresholds.

---

## 3. Directory Layout

```text
├── src/
│   ├── __init__.py
│   ├── schemas.py                      # Data contracts for Audio, Trust & Upstream Evidence
│   ├── audio_intelligence/
│   │   ├── __init__.py
│   │   └── assessor.py                 # Audio quality assessment (SNR, noise, speech duration)
│   └── trust_engine/
│       ├── __init__.py
│       ├── engine.py                   # Adaptive trust decision engine & recovery
│       └── mock_data.py                # Deterministic mock scenarios for independent testing
├── tests/
│   ├── __init__.py
│   └── test_initialization.py          # Phase 1 import, schema and contract tests
├── requirements-member3.txt            # Member 3 dependencies (Python 3.13 tested)
├── .gitignore                          # Excludes audio files, secrets, venvs, caches
└── README.md                           # Architecture and integration guide
```

---

## 4. Current Status: Phase 6 (Final Integration and Demo Completed)

| Feature | Phase | Status |
| :--- | :--- | :--- |
| Modular Folder Structure & Package Inits | Phase 1 | **Implemented** |
| .gitignore for Audio/Secrets/Caches | Phase 1 | **Implemented** |
| Baseline Interface Stubs (`assessor.py`, `engine.py`) | Phase 1 | **Implemented** |
| Audio Input Validation (Formats, Corrupt, Non-finite, Stereo/Mono) | Phase 2 | **Implemented** |
| Pre-downmix Multi-channel Clipping Detection | Phase 2 | **Implemented** |
| Anti-Phase Stereo Cancellation Defense | Phase 5 | **Implemented** |
| Frame-based Energy & Background Noise Estimation | Phase 2 | **Implemented** |
| Quality Classification (GOOD, MODERATE, POOR, INVALID) | Phase 2 | **Implemented** |
| Public API Function `analyze_audio()` | Phase 2 | **Implemented** |
| Normalized Multi-source Evidence Schemas (Audio, Aletheia, Eidos) | Phase 3 | **Implemented** |
| Categorical Semantic Conflict Resolution & Rule Precedence | Phase 3 / 4 | **Implemented** |
| Non-downgrade Invariant (Poor audio never weakens security) | Phase 3 | **Implemented** |
| Financial Transaction Multi-Factor Safeguard | Phase 3 | **Implemented** |
| Adaptive Recovery Engine & Action Prioritization (`recovery.py`) | Phase 4 | **Implemented** |
| Multi-turn Authentication Session State Machine (`AuthenticationSession`) | Phase 4 | **Implemented** |
| Bounded Retry Counters (Max 3 Audio, Max 2 Service) & TTL Expiry | Phase 4 | **Implemented** |
| Tamper-Resistant Evidence Binding & Stale/Cross-Session Checks | Phase 4 | **Implemented** |
| Suspicious Session Permanent Lockout Invariant | Phase 4 | **Implemented** |
| Deterministic Decision Explainer (`DecisionExplainer`) | Phase 4 | **Implemented** |
| Unified 2-Stage Pipeline Facade (`AnanthPipeline` in `src/pipeline.py`) | Phase 6 | **Implemented** |
| Standalone Interactive 9-Scenario Demonstration (`demo.py`) | Phase 6 | **Implemented** |
| Member 2 Integration Guide (`INTEGRATION_GUIDE.md`) | Phase 6 | **Implemented** |
| Hackathon Innovation & Judge Walkthrough (`DEMO_GUIDE.md`) | Phase 6 | **Implemented** |
| Comprehensive QA, Security & Performance Report (`TEST_REPORT.md`) | Phase 5 | **Implemented** |
| High-Resolution Benchmarking & Metrics Suite (`benchmarks/`) | Phase 5 | **Implemented** |
| Comprehensive Automated Test Suite (**69 Tests Passing**) | Phase 1 - 6 | **Implemented** |
| Live External API Credential Binding (Member 2 Integration Task) | Phase 6 | *Pending Partner API Credentials* |

---

## 5. Integration Guide for Member 2 (Backend / API)

Member 2 handles backend endpoints and communication with Aletheia & Eidos APIs. Here is how Member 2 connects with Member 3:

### Step 1: Pre-flight Audio Quality Check
Member 2 receives the caller audio stream/file and invokes the `AudioQualityAssessor`:

```python
from src.audio_intelligence.assessor import AudioQualityAssessor
import soundfile as sf

audio_data, sample_rate = sf.read("caller_audio.wav")
assessor = AudioQualityAssessor()
quality_report = assessor.assess_array(audio_data, sample_rate)

if not quality_report.is_usable_for_biometrics:
    # Stop processing; return immediate retry prompt to frontend
    return {"status": "RETRY_AUDIO", "reason": quality_report.quality_notes}
```

### Step 2: Adaptive Trust Evaluation
Once Aletheia and Eidos return verification scores, Member 2 constructs the evidence contract and requests a trust decision:

```python
from src.schemas import MockVerificationEvidence, ActionRiskLevel
from src.trust_engine.engine import AdaptiveTrustEngine

evidence = MockVerificationEvidence(
    caller_id="user_123",
    aletheia_liveness_score=aletheia_res.liveness_score,
    aletheia_confidence=aletheia_res.confidence,
    eidos_voice_match_score=eidos_res.match_score,
    eidos_confidence=eidos_res.confidence,
    requested_action_risk=ActionRiskLevel.HIGH
)

engine = AdaptiveTrustEngine()
outcome = engine.evaluate(evidence, quality_report)

# Member 2 sends outcome.to_dict() to Member 1 (Frontend)
```

---

## 6. How to Run Tests

From the repository root, run with the existing virtual environment:

```powershell
.\.venv\Scripts\pytest tests/ -v
```
