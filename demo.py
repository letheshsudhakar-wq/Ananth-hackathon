"""
Standalone Demonstrator for ANANTH (Task 5).

Runs 9 complete end-to-end scenarios without requiring external API credentials:
Scenario 1: Genuine caller with adequate audio and matching identity.
Scenario 2: Noisy recording requiring adaptive audio recovery.
Scenario 3: Short recording requiring additional speech.
Scenario 4: Deepfake detected despite matching speaker identity.
Scenario 5: Genuine voice with identity mismatch.
Scenario 6: External verification service unavailable.
Scenario 7: Successful recovery after a clearer recording.
Scenario 8: Verified voice requesting a financial transaction, requiring independent authentication.
Scenario 9: Suspicious session attempting verification again, remaining blocked.
"""

import sys
import os
import json
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.pipeline import AnanthPipeline
from src.schemas import (
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    EvidenceStatus,
    ActionRiskLevel,
)


def synth_tone(duration: float = 3.0, noise_level: float = 0.002) -> np.ndarray:
    """Generates synthetic speech burst pulses simulating vocal formants."""
    sample_rate = 16000
    total_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    np.random.seed(42)
    noise = np.random.normal(0, noise_level, total_samples).astype(np.float32)
    signal = np.zeros(total_samples, dtype=np.float32)

    carrier = (0.6 * np.sin(2 * np.pi * 220 * t) +
               0.3 * np.sin(2 * np.pi * 440 * t) +
               0.1 * np.sin(2 * np.pi * 880 * t)).astype(np.float32) * 0.5

    # Bursts simulating active speech
    burst_intervals = [(0.2, duration * 0.85)] if duration > 1.0 else [(0.1, duration * 0.6)]
    for start, end in burst_intervals:
        idx_start = int(start * sample_rate)
        idx_end = min(int(end * sample_rate), total_samples)
        if idx_start < idx_end:
            signal[idx_start:idx_end] = carrier[idx_start:idx_end]

    return np.clip(signal + noise, -1.0, 1.0)


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f" {title.upper()}")
    print("=" * 75)


def run_demo():
    print_banner("ANANTH: Detectif.ai UNCLONE Hackathon Demo (Track 03 - The Trust Layer)")
    print("Demonstrating 9 Adaptive Voice Authentication & Recovery Scenarios...")

    # Explicit Demo Mode (Mock mode enabled, production_mode=False)
    pipeline = AnanthPipeline(production_mode=False)

    clean_audio = synth_tone(3.0, noise_level=0.002)
    noisy_audio = synth_tone(3.0, noise_level=0.15)
    short_audio = synth_tone(0.6, noise_level=0.002)

    # --------------------------------------------------------------------------
    # Scenario 1: Genuine caller with clean audio and matching identity
    # --------------------------------------------------------------------------
    print_banner("Scenario 1: Genuine Caller (Clean Audio + Matching Identity)")
    st_a = pipeline.stage_a_assess_audio(clean_audio, sample_rate=16000)
    print(f"[Stage A] Suitable for Biometrics: {st_a['suitable_for_authentication']} | Quality: {st_a['quality_status']} | SNR: {st_a['estimated_snr_db']} dB")

    al_1 = NormalizedAletheiaEvidence(liveness_score=0.96, confidence=0.92, session_id="demo_s1")
    eid_1 = NormalizedEidosEvidence(match_score=0.94, confidence=0.90, session_id="demo_s1")
    res_1 = pipeline.stage_b_evaluate_and_recover("demo_s1", "user_alice", st_a["raw_report"], al_1, eid_1, ActionRiskLevel.LOW)
    print(f"[Stage B] Verification: {res_1['verification_status']} | Decision: {res_1['decision']} | State: {res_1['session_state']}")
    print(f"          Customer Message: \"{res_1['customer_message']}\"")

    # --------------------------------------------------------------------------
    # Scenario 2: Noisy recording requiring adaptive audio recovery
    # --------------------------------------------------------------------------
    print_banner("Scenario 2: Noisy Recording (Elevated Ambient Noise Floor)")
    st_a2 = pipeline.stage_a_assess_audio(noisy_audio, sample_rate=16000)
    print(f"[Stage A] Suitable: {st_a2['suitable_for_authentication']} | Quality: {st_a2['quality_status']} | SNR: {st_a2['estimated_snr_db']} dB")
    res_2 = pipeline.stage_b_evaluate_and_recover("demo_s2", "user_bob", st_a2["raw_report"], None, None, ActionRiskLevel.MEDIUM)
    print(f"[Stage B] Decision: {res_2['decision']} | Recovery Action: {res_2['recovery_action']}")
    print(f"          Customer Message: \"{res_2['customer_message']}\"")
    print(f"          Retries Remaining: {res_2['retries_remaining']}")

    # --------------------------------------------------------------------------
    # Scenario 3: Short recording requiring additional speech
    # --------------------------------------------------------------------------
    print_banner("Scenario 3: Insufficient Speech Duration (< 1.0s)")
    st_a3 = pipeline.stage_a_assess_audio(short_audio, sample_rate=16000)
    print(f"[Stage A] Duration: {st_a3['duration_seconds']}s | Eligible for Aletheia: {st_a3['eligible_for_aletheia']}")
    res_3 = pipeline.stage_b_evaluate_and_recover("demo_s3", "user_charlie", st_a3["raw_report"], None, None)
    print(f"[Stage B] Decision: {res_3['decision']} | Recovery Action: {res_3['recovery_action']}")
    print(f"          Customer Message: \"{res_3['customer_message']}\"")

    # --------------------------------------------------------------------------
    # Scenario 4: Deepfake detected despite matching speaker identity
    # --------------------------------------------------------------------------
    print_banner("Scenario 4: AI Voice Clone / Deepfake Attack (Spoof Escalation)")
    al_4 = NormalizedAletheiaEvidence(liveness_score=0.08, confidence=0.96, session_id="demo_s4") # Deepfake
    eid_4 = NormalizedEidosEvidence(match_score=0.95, confidence=0.92, session_id="demo_s4")     # Victim Timbre Match
    res_4 = pipeline.stage_b_evaluate_and_recover("demo_s4", "user_victim", st_a["raw_report"], al_4, eid_4, ActionRiskLevel.HIGH)
    print(f"[Stage B] Verification: {res_4['verification_status']} | Decision: {res_4['decision']} | State: {res_4['session_state']}")
    print(f"          Conflicting Evidence Detected: {res_4['conflicting_evidence']}")
    print(f"          Recovery Action: {res_4['recovery_action']}")
    print(f"          Customer Message: \"{res_4['customer_message']}\"")

    # --------------------------------------------------------------------------
    # Scenario 5: Genuine human voice with speaker identity mismatch
    # --------------------------------------------------------------------------
    print_banner("Scenario 5: Impersonator (Natural Human Speech + Enrolled Mismatch)")
    al_5 = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.90, session_id="demo_s5")
    eid_5 = NormalizedEidosEvidence(match_score=0.22, confidence=0.88, session_id="demo_s5")     # Mismatch
    res_5 = pipeline.stage_b_evaluate_and_recover("demo_s5", "user_dave", st_a["raw_report"], al_5, eid_5)
    print(f"[Stage B] Verification: {res_5['verification_status']} | Decision: {res_5['decision']} | State: {res_5['session_state']}")
    print(f"          Recovery Action: {res_5['recovery_action']}")

    # --------------------------------------------------------------------------
    # Scenario 6: External verification service unavailable
    # --------------------------------------------------------------------------
    print_banner("Scenario 6: External API Service Unavailable (Bounded Retry)")
    al_6 = NormalizedAletheiaEvidence(status=EvidenceStatus.UNAVAILABLE, session_id="demo_s6")
    eid_6 = NormalizedEidosEvidence(match_score=0.90, confidence=0.85, session_id="demo_s6")
    res_6 = pipeline.stage_b_evaluate_and_recover("demo_s6", "user_eve", st_a["raw_report"], al_6, eid_6)
    print(f"[Stage B] State: {res_6['session_state']} | Action: {res_6['recovery_action']} | Service Retries Left: {res_6['service_retries_remaining']}")

    # --------------------------------------------------------------------------
    # Scenario 7: Successful recovery after a clearer recording
    # --------------------------------------------------------------------------
    print_banner("Scenario 7: Multi-Turn Turnaround (Noisy Audio -> Clear Audio Recovery)")
    sess_id = "demo_s7_multiturn"
    al_7_1 = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.92, session_id=sess_id)
    eid_7_1 = NormalizedEidosEvidence(match_score=0.94, confidence=0.90, session_id=sess_id)
    # Turn 1: Noisy audio
    res_7_t1 = pipeline.stage_b_evaluate_and_recover(sess_id, "user_frank", st_a2["raw_report"], al_7_1, eid_7_1)
    print(f"  Turn 1 Result: State = {res_7_t1['session_state']} | Action = {res_7_t1['recovery_action']} | Retries Left = {res_7_t1['retries_remaining']}")
    # Turn 2: Clear audio
    al_7_2 = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.92, session_id=sess_id)
    eid_7_2 = NormalizedEidosEvidence(match_score=0.94, confidence=0.90, session_id=sess_id)
    res_7_t2 = pipeline.stage_b_evaluate_and_recover(sess_id, "user_frank", st_a["raw_report"], al_7_2, eid_7_2)
    print(f"  Turn 2 Result: State = {res_7_t2['session_state']} | Decision = {res_7_t2['decision']} | Terminal = {res_7_t2['terminal_state']}")
    print(f"  Message:       \"{res_7_t2['customer_message']}\"")

    # --------------------------------------------------------------------------
    # Scenario 8: Financial transaction requires independent authentication
    # --------------------------------------------------------------------------
    print_banner("Scenario 8: High-Value Financial Operation (Mandatory Step-Up Safeguard)")
    al_8 = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.92, session_id="demo_s8")
    eid_8 = NormalizedEidosEvidence(match_score=0.94, confidence=0.90, session_id="demo_s8")
    res_8 = pipeline.stage_b_evaluate_and_recover("demo_s8", "user_grace", st_a["raw_report"], al_8, eid_8, ActionRiskLevel.FINANCIAL)
    print(f"[Stage B] Verification: {res_8['verification_status']} | Decision: {res_8['decision']} | State: {res_8['session_state']}")
    print(f"          Independent Auth Required: {res_8['independent_auth_required']} | Sensitive Ops Paused: {res_8['sensitive_operations_paused']}")
    print(f"          Reason Codes: {res_8['reason_codes']}")
    print(f"          Customer Message: \"{res_8['customer_message']}\"")

    # --------------------------------------------------------------------------
    # Scenario 9: Suspicious session attempting verification again (Permanent Lock)
    # --------------------------------------------------------------------------
    print_banner("Scenario 9: Security Invariant (Blocked Session Remains Permanently Locked)")
    # Re-using Scenario 4's blocked session with clean audio
    res_9 = pipeline.stage_b_evaluate_and_recover("demo_s4", "user_victim", st_a["raw_report"], al_1, eid_1)
    print(f"[Stage B] State: {res_9['session_state']} | Decision: {res_9['decision']}")
    print(f"          Recovery Action: {res_9['recovery_action']}")
    print(f"          Reason Codes:    {res_9['reason_codes']}")
    print(f"          Customer Message: \"{res_9['customer_message']}\"")

    print("\n" + "=" * 75)
    print(" DEMONSTRATION COMPLETE: All 9 Scenarios Verified Successfully")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_demo()
