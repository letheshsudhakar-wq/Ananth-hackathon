"""
Evaluation and Metrics Runner for ANANTH Member 3 (Task 7).

Computes:
- Total test cases & pass rate
- Unsafe acceptance count in tested scenarios
- Rejection metrics across mock scenarios
- Recovery success rate in multi-turn simulations
- Performance benchmarks across audio lengths
"""

import sys
import os
import time
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from benchmarks.benchmark_pipeline import benchmark_pipeline
from src.schemas import (
    AudioQualityReport,
    AudioQualityStatus,
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    ActionRiskLevel,
    VerificationStatus,
    TrustDecision,
    RecommendedAction,
    ReasonCode,
)
from src.trust_engine.engine import AdaptiveTrustEngine
from src.trust_engine.recovery import AdaptiveRecoveryEngine


def run_evaluation():
    print("=" * 60)
    print("ANANTH - Member 3 Evaluation Metrics Runner")
    print("Track 03 – The Trust Layer | UNCLONE by Detectif.ai")
    print("=" * 60)

    # 1. Run full test suite through pytest programmatically
    print("\n[1/3] Running Full Test Suite...")
    exit_code = pytest.main(["tests/", "-q"])

    # 2. Run Adversarial & Scenario Evaluation
    print("\n[2/3] Evaluating Decision Invariants on Labeled Scenarios...")
    engine = AdaptiveTrustEngine(production_mode=False)

    clean_audio = AudioQualityReport(
        valid=True, quality_status=AudioQualityStatus.GOOD, suitable_for_authentication=True,
        duration_seconds=3.0, estimated_speech_duration_seconds=2.5, sample_rate=16000,
        channel_count=1, estimated_noise_level_dbfs=-55.0, estimated_snr_db=25.0,
        silence_percentage=10.0, clipping_percentage=0.0, rms_dbfs=-20.0, peak_amplitude=0.6,
        detected_issues=[], recommended_action=RecommendedAction.PROCEED
    )
    poor_audio = AudioQualityReport(
        valid=True, quality_status=AudioQualityStatus.POOR, suitable_for_authentication=False,
        duration_seconds=0.8, estimated_speech_duration_seconds=0.2, sample_rate=16000,
        channel_count=1, estimated_noise_level_dbfs=-20.0, estimated_snr_db=4.0,
        silence_percentage=75.0, clipping_percentage=5.0, rms_dbfs=-15.0, peak_amplitude=1.0,
        detected_issues=[], recommended_action=RecommendedAction.REQUEST_FRESH_RECORDING
    )

    labeled_scenarios = [
        # (name, aletheia_score, aletheia_conf, eidos_score, eidos_conf, audio, risk, expected_verif, expected_dec, is_attack)
        ("Legitimate Low Risk", 0.95, 0.90, 0.92, 0.88, clean_audio, ActionRiskLevel.LOW, VerificationStatus.VERIFIED, TrustDecision.ALLOW, False),
        ("Legitimate Financial", 0.95, 0.90, 0.92, 0.88, clean_audio, ActionRiskLevel.FINANCIAL, VerificationStatus.VERIFIED, TrustDecision.STEP_UP_CHALLENGE, False),
        ("Deepfake Voice Clone", 0.10, 0.95, 0.94, 0.90, clean_audio, ActionRiskLevel.HIGH, VerificationStatus.SUSPICIOUS, TrustDecision.DENY, True),
        ("Impersonator Human Mismatch", 0.95, 0.90, 0.20, 0.90, clean_audio, ActionRiskLevel.MEDIUM, VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED, TrustDecision.STEP_UP_CHALLENGE, False),
        ("Clean Score Poor Audio", 0.95, 0.90, 0.92, 0.88, poor_audio, ActionRiskLevel.LOW, VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED, TrustDecision.RETRY_AUDIO, False),
        ("Deepfake Poor Audio", 0.10, 0.95, 0.30, 0.70, poor_audio, ActionRiskLevel.HIGH, VerificationStatus.SUSPICIOUS, TrustDecision.DENY, True),
    ]

    unsafe_acceptance_count = 0
    correct_decision_count = 0

    for name, al_s, al_c, eid_s, eid_c, aud, risk, exp_v, exp_d, is_attack in labeled_scenarios:
        al = NormalizedAletheiaEvidence(liveness_score=al_s, confidence=al_c)
        eid = NormalizedEidosEvidence(match_score=eid_s, confidence=eid_c)
        res = engine.evaluate({}, aud, al, eid, risk)

        # Check unsafe acceptance (adversarial breach)
        if is_attack and res.decision == TrustDecision.ALLOW:
            unsafe_acceptance_count += 1
        if not aud.suitable_for_authentication and res.decision == TrustDecision.ALLOW:
            unsafe_acceptance_count += 1

        if res.verification_status == exp_v and res.decision == exp_d:
            correct_decision_count += 1

    # 3. Multi-turn Recovery Simulation
    print("\n[3/3] Evaluating Multi-Turn Recovery Simulations...")
    recovery = AdaptiveRecoveryEngine()
    session = recovery.get_or_create_session("eval_sess_01", "eval_caller")

    # Turn 1: Poor audio -> Turn 2: Good audio
    al = NormalizedAletheiaEvidence(liveness_score=0.92, confidence=0.88, session_id="eval_sess_01")
    eid = NormalizedEidosEvidence(match_score=0.90, confidence=0.85, session_id="eval_sess_01")
    t1_out = engine.evaluate({}, poor_audio, al, eid)
    r1 = recovery.process_turn(session, poor_audio, t1_out, al, eid)
    t2_out = engine.evaluate({}, clean_audio, al, eid)
    r2 = recovery.process_turn(session, clean_audio, t2_out, al, eid)
    recovery_succeeded = (r1.decision == TrustDecision.RETRY_AUDIO and r2.decision == TrustDecision.ALLOW)

    # 4. Latency Benchmarks
    bench_data = benchmark_pipeline(iterations=15)

    summary = {
        "pytest_exit_code": int(exit_code),
        "total_labeled_scenarios": len(labeled_scenarios),
        "correct_decisions": correct_decision_count,
        "unsafe_acceptance_count": unsafe_acceptance_count,
        "recovery_simulation_success": recovery_succeeded,
        "benchmarks": bench_data,
    }

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total Labeled Test Scenarios: {len(labeled_scenarios)}")
    print(f"Correct Decisions:            {correct_decision_count}/{len(labeled_scenarios)}")
    print(f"Unsafe Acceptance Breaches:   {unsafe_acceptance_count} (Security Invariant: 0 allowed)")
    print(f"Recovery Simulation:          {'SUCCESS' if recovery_succeeded else 'FAILED'}")
    print("\nPerformance Latency (Local Compute):")
    for key, val in bench_data.items():
        print(f"  {key}: Median = {val['e2e_local_median_ms']} ms | p95 = {val['e2e_local_p95_ms']} ms (DSP = {val['audio_dsp_median_ms']} ms)")

    return summary


if __name__ == "__main__":
    run_evaluation()
