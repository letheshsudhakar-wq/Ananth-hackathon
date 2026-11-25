# ANANTH — Phase 5 QA, Security & Performance Test Report

Track: **Track 03 – The Trust Layer | UNCLONE by Detectif.ai**  
Module: **Member 3 — Audio Intelligence, Adaptive Trust Engine, Recovery, Explainability & Testing**

---

## 1. Test Methodology

The testing architecture for ANANTH Member 3 operates across 4 distinct testing levels:
1. **Physical Acoustic & DSP Signal Processing Tests**: Deterministic synthetic waveforms (white noise, simulated traffic rumble, crowd babble, transient bursts, silence, clipped signals, multi-channel stereo phase shifts, standard telephony/VoIP rates).
2. **Deterministic Security Boundary Tests**: Parameterized evaluation of exact decision thresholds ($0.699$ vs $0.700$, $0.749$ vs $0.750$, $0.350$ vs $0.351$) and fail-closed handling for malformed or unknown inputs.
3. **Multi-Turn Recovery State Machine Verification**: Lifecycle simulations including acoustic retry paths, service retry exhaustion, session timeouts, and permanent lockouts.
4. **Adversarial & Replay-Resistance Invariants**: Cross-session evidence rejection, stale timestamp enforcement, and verification that suspicious/blocked sessions cannot be unlocked by submitting fresh recordings.

> **Disclaimer**: Synthetic signals and deterministic mock scenarios are designed for testing signal-processing algorithms, decision trees, and state machine transitions. They do **not** claim or represent real-world biometric accuracy, False Acceptance Rates (FAR), False Rejection Rates (FRR), or live speaker verification under production conditions.

---

## 2. Test Execution Summary

| Test Suite File | Focus Area | Total Tests | Passed | Failed |
| :--- | :--- | :--- | :--- | :--- |
| `tests/test_initialization.py` | Imports, schemas, baseline contracts | 4 | 4 | 0 |
| `tests/test_audio_intelligence.py` | Ingestion, feature extraction, clipping, SNR | 13 | 13 | 0 |
| `tests/test_audio_edge_cases.py` | Noise profiles, anti-phase stereo, oversized buffers | 11 | 11 | 0 |
| `tests/test_trust_engine.py` | Evidence normalization, rule precedence, safeguards | 15 | 15 | 0 |
| `tests/test_security_invariants.py` | Boundary precision, malformed risk tiers, deepfakes | 9 | 9 | 0 |
| `tests/test_recovery_and_explainer.py` | Multi-turn retries, state machine, explanation privacy | 9 | 9 | 0 |
| `tests/test_recovery_edge_cases.py` | Repeated failed attempts, non-contradictory messages | 2 | 2 | 0 |
| **TOTAL** | **Full Automated Test Suite** | **63** | **63** | **0** |

- **Pass Rate**: 100% (63 passed in 0.48s)
- **Unsafe Acceptance Breaches**: **0** (Zero attacks or degraded audio accepted)

---

## 3. Bugs Discovered & Fixed During Phase 5 Audit

1. **Anti-Phase Stereo Cancellation Bug**:
   - *Issue*: When input audio had stereo channels exactly out of phase (Left = $-Right$), standard `np.mean(data, axis=1)` canceled out the entire acoustic signal to pure zero, falsely classifying clean speech as silent.
   - *Fix*: Added normalized vector correlation detection ($\text{corr} < -0.98$). If anti-phase cancellation is detected, the engine analyzes channel 0 directly rather than collapsing to silence.
2. **Missing Input Buffer Guardrail on Direct Numpy Arrays**:
   - *Issue*: In-memory NumPy arrays bypassed maximum duration limits before downstream frame allocation.
   - *Fix*: Added strict pre-allocation sample count validation ($> 2 \times \text{max\_duration} \times \text{sample\_rate}$) raising `EXCESSIVE_DURATION` before expensive computations.
3. **Unbound Variable on Malformed Risk Tiers**:
   - *Issue*: In `engine.py`, parsing malformed risk tiers had a scope sequencing error where `risk_level` was evaluated before normalization.
   - *Fix*: Re-sequenced input normalization to guarantee unknown or malicious risk strings immediately fail closed with `INVALID_EVIDENCE_PAYLOAD` and action `DENY`.
4. **Permanent Block vs. Expiry Precedence**:
   - *Issue*: A blocked session evaluated after its timeout window was transitioning to `EXPIRED`.
   - *Fix*: Updated `AuthenticationSession.check_and_update_expiry()` so that once a session is `BLOCKED` (due to deepfake or security lockout), it remains permanently blocked and cannot transition to expired.

---

## 4. Performance Benchmarks (Local Compute Latency)

Benchmarks were executed locally using high-resolution profiling (`time.perf_counter()`) across 25 iterations on representative audio lengths:

| Audio Length | Audio DSP (Median) | Audio DSP (p95) | Trust Engine (Median) | Recovery + Explainer | End-to-End Local Total |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **5 Seconds** | 1.04 ms | 1.53 ms | 0.013 ms | 0.042 ms | **1.10 ms** |
| **10 Seconds** | 1.42 ms | 2.41 ms | 0.014 ms | 0.043 ms | **1.48 ms** |
| **30 Seconds** | 5.27 ms | 6.32 ms | 0.021 ms | 0.054 ms | **5.37 ms** |

*Key Findings*:
- DSP feature extraction scales linearly with audio length ($~5.3\text{ ms}$ for a full 30-second recording).
- Trust Engine decision logic and Recovery State Machine evaluate in under **0.05 ms** ($50\text{ }\mu\text{s}$).
- Zero external network dependencies inside Member 3 modules.

---

## 5. Security Safeguards Tested

| Safeguard | Test Scenario | Outcome |
| :--- | :--- | :--- |
| **Deepfake Attack Escalation** | Spoof score $\le 0.35$ with 100% voice timbre match and pristine audio | **DENY** (`SUSPICIOUS`) |
| **Identity Mismatch** | Verified authentic human voice but enrolled timbre divergence | **STEP_UP_CHALLENGE** (`ADDITIONAL_VERIFICATION_REQUIRED`) |
| **Financial Operation Gate** | Legitimate voice verification on `FINANCIAL` risk tier | **STEP_UP_CHALLENGE** (Voice alone cannot authorize funds) |
| **Non-Downgrade Invariant** | Degraded / clipped audio with passing biometric scores | **RETRY_AUDIO** (Never bypasses verification) |
| **Tamper Resistance** | Replay of evidence from another session (`session_id` mismatch) | **DENY** (`CROSS_SESSION_EVIDENCE_REJECTED`) |
| **Stale Evidence Guard** | Evidence timestamped $> 60\text{s}$ prior to turn | **DENY** (`STALE_EVIDENCE_REJECTED`) |
| **Permanent Lockout** | Submission of genuine audio to a previously blocked session | **DENY** (`SESSION_LOCKED_SUSPICIOUS`) |
| **Threshold Privacy** | Customer-facing explainer output | Zero numeric scores or internal thresholds leaked |

---

## 6. Manual Testing Checklist (for Consented Recordings)

When live multilingual or multi-speaker customer recordings are tested:
- [ ] Verify that background ambient phone noise does not falsely trigger deepfake detection.
- [ ] Confirm natural accent variations are not categorized as poor acoustic quality.
- [ ] Ensure customer audio files are never written to disk or logged in plain text.
- [ ] Test graceful retry prompts when a caller speaks with weak microphone sensitivity.

---

## 7. How to Run Tests & Benchmarks

From the repository root using the virtual environment:

```powershell
# Run full automated test suite (63 tests)
.\.venv\Scripts\pytest tests/ -v

# Run performance benchmarking script
.\.venv\Scripts\python.exe benchmarks/benchmark_pipeline.py

# Run evaluation metrics runner
.\.venv\Scripts\python.exe benchmarks/run_evaluation.py
```
