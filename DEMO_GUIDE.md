# ANANTH — Hackathon Demonstration & Innovation Guide

**Track 03 – The Trust Layer | UNCLONE by Detectif.ai**  
**Core Motto**: *"Don't just detect fraud. Recover trust."*

---

## 1. Problem Statement

Voice biometrics in real-world telephony, banking, and customer support face severe operational challenges:
1. **Unreliable Acoustic Environments**: Background street noise, low microphone gain, digital clipping, and cellular packet loss frequently cause legitimate callers to be falsely rejected or rejected without explanation.
2. **Adversarial Generative Deepfakes**: Attackers use AI voice cloning to mimic the exact vocal timbre of legitimate victims, fooling standard speaker recognition systems.
3. **Fragile Single-Score Systems**: Existing authentication engines either blindly average scores or fail closed without recovery, forcing frustrated genuine customers to abandon calls.

---

## 2. ANANTH's Core Innovations (The Trust Layer)

ANANTH introduces three major architectural innovations:

### Innovation 1: Adaptive Audio Intelligence (Pre-Flight Acoustic Quality Gating)
Instead of blindly sending poor-quality or silent recordings to expensive biometric APIs, ANANTH inspects the raw physical signal in **under 1.5 milliseconds**. It calculates SNR, active speech duration, noise floor, and digital clipping before biometrics are computed. Degraded audio triggers immediate, targeted recovery prompts (`SPEAK_CLOSER_TO_MIC`, `REDUCE_MICROPHONE_GAIN`) without wasting API credits or reducing security thresholds.

### Innovation 2: Confidence-Aware Adaptive Trust Engine
Rather than computing naive mathematical averages of unrelated biometric scores, ANANTH separates:
- **Authenticity (Anti-Spoof Liveness)**: Evaluates whether biological human vocal tract dynamics are present.
- **Identity (Speaker Recognition)**: Evaluates whether the voice matches the enrolled customer.
- **Conflict Resolution**: If an AI voice clone passes speaker match (timbre match) but fails liveness, the engine escalates immediately to `SUSPICIOUS` / `DENY`. Credible attacks are **never** overridden by high speaker match scores or good audio quality.

### Innovation 3: Adaptive Multi-Turn Authentication Recovery
When uncertainty arises (noisy audio, low model confidence, or API timeouts), ANANTH does not simply reject the customer. It executes a **state-machine-driven recovery workflow**:
- Bounded acoustic retries (max 3 attempts).
- Automatic service retries (max 2 attempts).
- Escalation to secondary out-of-band verification without lowering thresholds.
- Permanent lockout if malicious synthetic attacks are detected.

---

## 3. System Architecture & Member 3's Contribution

```text
[Frontend / Mobile UI (Member 1)]
              ▲
              │ HTTP / JSON
              ▼
[Backend API Gateway (Member 2)]
  │                              ▲
  │ (Raw Audio)                  │ (Normalized Evidence)
  ▼                              │
┌────────────────────────────────┴─────────────────────────────┐
│ MEMBER 3 CORE MODULES:                                       │
│                                                              │
│  [Stage A: Audio Intelligence Engine]                        │
│   ├── Loader & Format Validator (Anti-phase stereo guard)    │
│   ├── Feature Extractor (Frame SNR, Noise Floor, VAD)        │
│   └── Audio Quality Assessor (Quality status, acoustic tips) │
│                                                              │
│  [Stage B: Adaptive Trust Engine & Recovery]                 │
│   ├── Normalization & Boundary Validations (Range, NaN, Inf) │
│   ├── Deterministic Conflict Resolver & Security Rules       │
│   ├── Multi-Turn Session State Machine (Bounds, Timers)      │
│   └── Explainable Decision Engine (Customer vs Audit Logs)   │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. 9-Scenario Demonstration Walkthrough

You can execute the entire live interactive demonstration by running:

```powershell
python demo.py
```

### Demonstration Scenarios:
1. **Scenario 1: Genuine Caller**:
   - Clean audio + high liveness ($0.96$) + high speaker match ($0.94$).
   - *Outcome*: `VERIFIED` $\rightarrow$ `ALLOW`.
2. **Scenario 2: Noisy Recording**:
   - Elevated ambient background noise (SNR $5\text{ dB}$).
   - *Outcome*: `ADDITIONAL_VERIFICATION_REQUIRED` $\rightarrow$ `RETRY_AUDIO` with action `REQUEST_QUIETER_ENVIRONMENT`.
3. **Scenario 3: Short Recording**:
   - Recording under minimum duration threshold ($0.6\text{s}$).
   - *Outcome*: `RETRY_AUDIO` with action `REQUEST_LONGER_RECORDING`.
4. **Scenario 4: AI Voice Clone / Deepfake Attack**:
   - Liveness fails ($0.08$) despite high speaker match ($0.95$).
   - *Outcome*: `SUSPICIOUS` $\rightarrow$ `DENY` with conflicting evidence flagged and session locked.
5. **Scenario 5: Impersonator**:
   - Genuine human speech ($0.95$) with speaker identity mismatch ($0.22$).
   - *Outcome*: `ADDITIONAL_VERIFICATION_REQUIRED` $\rightarrow$ `STEP_UP_CHALLENGE`.
6. **Scenario 6: External Service Outage**:
   - Aletheia temporarily unavailable.
   - *Outcome*: Bounded service retry attempt ($1/2$) without requiring the customer to re-record.
7. **Scenario 7: Multi-Turn Turnaround**:
   - Turn 1 fails due to noise; Turn 2 succeeds with clear audio $\rightarrow$ `VOICE_VERIFIED`.
8. **Scenario 8: Financial Operation Safeguard**:
   - Verified voice requesting fund transfer. Mandatory step-up enforced (`STEP_UP_CHALLENGE`). Voice alone cannot authorize funds.
9. **Scenario 9: Blocked Session Invariant**:
   - Attacker attempts to submit clean audio to a previously blocked session $\rightarrow$ Session remains permanently `BLOCKED`.

---

## 5. Actual Verified Testing & Benchmark Results

- **Automated Test Suite**: **63 passed, 0 failed** in $0.77\text{ seconds}$.
- **Unsafe Acceptance Breaches**: **0** across all boundary and adversarial scenarios.
- **Local Compute Latency**:
  - $5\text{s}$ Audio: **$1.10\text{ ms}$**
  - $10\text{s}$ Audio: **$1.48\text{ ms}$**
  - $30\text{s}$ Audio: **$5.37\text{ ms}$**

---

## 6. Disclaimers & Non-Claims

- **Biometric Accuracy**: Synthetic waveforms and mock evidence demonstrate algorithmic decision logic, state transitions, and signal-processing edge cases. They do **not** claim real-world False Acceptance Rates (FAR) or False Rejection Rates (FRR).
- **Replay & Multilingual Recognition**: Full replay detection and cross-language phonetic invariance require live integration with Detectif.ai's production Aletheia and Eidos models during Phase 6.
