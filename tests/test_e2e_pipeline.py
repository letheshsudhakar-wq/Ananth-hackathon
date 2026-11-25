"""
End-to-End Unified Pipeline Integration Tests (Task 7).

Tests:
1. End-to-end Stage A & Stage B flow with clean audio.
2. End-to-end Stage A immediate rejection for bad audio.
3. End-to-end deepfake attack escalation and conflicting evidence detection.
4. End-to-end financial transaction mandatory step-up.
5. End-to-end JSON serialization compatibility for Member 1 & 2.
6. Mock evidence rejected when AnanthPipeline is instantiated with production_mode=True.
"""

import json
import pytest
import numpy as np

from src.pipeline import AnanthPipeline
from src.schemas import (
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    ActionRiskLevel,
    VerificationStatus,
    TrustDecision,
    SessionState,
    ReasonCode,
)


@pytest.fixture
def clean_audio_array() -> np.ndarray:
    sample_rate = 16000
    duration = 3.0
    total_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    np.random.seed(42)
    noise = np.random.normal(0, 0.002, total_samples).astype(np.float32)
    signal = np.zeros(total_samples, dtype=np.float32)
    carrier = (0.6 * np.sin(2 * np.pi * 220 * t) +
               0.3 * np.sin(2 * np.pi * 440 * t) +
               0.1 * np.sin(2 * np.pi * 880 * t)).astype(np.float32) * 0.5
    burst_intervals = [(0.2, 2.6)]
    for start, end in burst_intervals:
        idx_start = int(start * sample_rate)
        idx_end = min(int(end * sample_rate), total_samples)
        signal[idx_start:idx_end] = carrier[idx_start:idx_end]
    return np.clip(signal + noise, -1.0, 1.0)


def test_e2e_clean_verification_flow(clean_audio_array):
    """Stage A assess -> Stage B evaluate -> Verified ALLOW."""
    pipeline = AnanthPipeline(production_mode=False)
    sess_id = "e2e_clean_01"

    # Stage A
    st_a = pipeline.stage_a_assess_audio(clean_audio_array, sample_rate=16000)
    assert st_a["suitable_for_authentication"] is True
    assert st_a["eligible_for_aletheia"] is True
    assert st_a["eligible_for_eidos"] is True

    # Stage B
    al = NormalizedAletheiaEvidence(liveness_score=0.96, confidence=0.92)
    eid = NormalizedEidosEvidence(match_score=0.94, confidence=0.90)
    resp = pipeline.stage_b_evaluate_and_recover(
        session_id=sess_id,
        caller_id="user_alice",
        audio_report=st_a["raw_report"],
        aletheia_evidence=al,
        eidos_evidence=eid,
        action_risk_level=ActionRiskLevel.LOW,
    )

    assert resp["verification_status"] == VerificationStatus.VERIFIED.value
    assert resp["decision"] == TrustDecision.ALLOW.value
    assert resp["session_state"] == SessionState.VOICE_VERIFIED.value
    assert resp["sensitive_operations_paused"] is False
    assert resp["independent_auth_required"] is False
    assert resp["terminal_state"] is True


def test_e2e_stage_a_immediate_bad_audio_handling():
    """Stage A catches silent or clipped audio and immediately routes to retry."""
    pipeline = AnanthPipeline(production_mode=False)
    silent_audio = np.zeros(16000 * 3, dtype=np.float32)

    st_a = pipeline.stage_a_assess_audio(silent_audio, sample_rate=16000)
    assert st_a["suitable_for_authentication"] is False
    assert st_a["eligible_for_aletheia"] is False

    # Route straight to Stage B without calling external APIs
    resp = pipeline.stage_b_evaluate_and_recover(
        session_id="e2e_bad_02",
        caller_id="user_bob",
        audio_report=st_a["raw_report"],
    )

    assert resp["decision"] == TrustDecision.RETRY_AUDIO.value
    assert resp["session_state"] == SessionState.RETRY_AUDIO.value
    assert resp["sensitive_operations_paused"] is True


def test_e2e_deepfake_escalation_and_conflicts(clean_audio_array):
    """Deepfake attack with victim timbre match correctly triggers SUSPICIOUS / DENY."""
    pipeline = AnanthPipeline(production_mode=False)
    sess_id = "e2e_deepfake_03"

    st_a = pipeline.stage_a_assess_audio(clean_audio_array, sample_rate=16000)
    al = NormalizedAletheiaEvidence(liveness_score=0.10, confidence=0.95) # Synthetic spoof
    eid = NormalizedEidosEvidence(match_score=0.95, confidence=0.90)     # Timbre match

    resp = pipeline.stage_b_evaluate_and_recover(
        session_id=sess_id,
        caller_id="user_victim",
        audio_report=st_a["raw_report"],
        aletheia_evidence=al,
        eidos_evidence=eid,
        action_risk_level=ActionRiskLevel.HIGH,
    )

    assert resp["verification_status"] == VerificationStatus.SUSPICIOUS.value
    assert resp["decision"] == TrustDecision.DENY.value
    assert resp["conflicting_evidence"] is True
    assert resp["session_state"] == SessionState.BLOCKED.value
    assert resp["sensitive_operations_paused"] is True
    assert ReasonCode.CREDIBLE_DEEPFAKE_DETECTED.value in resp["reason_codes"]


def test_e2e_financial_transaction_mandatory_step_up(clean_audio_array):
    """Financial transaction enforces step-up even with verified voice."""
    pipeline = AnanthPipeline(production_mode=False)
    sess_id = "e2e_fin_04"

    st_a = pipeline.stage_a_assess_audio(clean_audio_array, sample_rate=16000)
    al = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.90)
    eid = NormalizedEidosEvidence(match_score=0.95, confidence=0.90)

    resp = pipeline.stage_b_evaluate_and_recover(
        session_id=sess_id,
        caller_id="user_charlie",
        audio_report=st_a["raw_report"],
        aletheia_evidence=al,
        eidos_evidence=eid,
        action_risk_level=ActionRiskLevel.FINANCIAL,
    )

    assert resp["verification_status"] == VerificationStatus.VERIFIED.value
    assert resp["decision"] == TrustDecision.STEP_UP_CHALLENGE.value
    assert resp["session_state"] == SessionState.STEP_UP_REQUIRED.value
    assert resp["independent_auth_required"] is True
    assert resp["sensitive_operations_paused"] is True
    assert ReasonCode.FINANCIAL_TRANSACTION_STEP_UP_REQUIRED.value in resp["reason_codes"]


def test_e2e_json_serialization(clean_audio_array):
    """Ensures complete response is 100% JSON-serializable for Member 1 frontend."""
    pipeline = AnanthPipeline(production_mode=False)
    st_a = pipeline.stage_a_assess_audio(clean_audio_array, sample_rate=16000)
    al = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.90)
    eid = NormalizedEidosEvidence(match_score=0.95, confidence=0.90)

    resp = pipeline.stage_b_evaluate_and_recover(
        session_id="e2e_json_05",
        caller_id="user_david",
        audio_report=st_a["raw_report"],
        aletheia_evidence=al,
        eidos_evidence=eid,
    )

    # Must serialize without TypeError
    serialized = json.dumps(resp)
    deserialized = json.loads(serialized)
    assert deserialized["session_id"] == "e2e_json_05"
    assert "customer_message" in deserialized
    assert "verification_status" in deserialized


def test_e2e_production_mode_rejects_mock_evidence(clean_audio_array):
    """When AnanthPipeline is instantiated with production_mode=True, mock evidence is denied."""
    pipeline = AnanthPipeline(production_mode=True)
    st_a = pipeline.stage_a_assess_audio(clean_audio_array, sample_rate=16000)

    al = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.90, is_mock=True)
    eid = NormalizedEidosEvidence(match_score=0.95, confidence=0.90, is_mock=True)

    resp = pipeline.stage_b_evaluate_and_recover(
        session_id="e2e_prod_06",
        caller_id="user_eve",
        audio_report=st_a["raw_report"],
        aletheia_evidence=al,
        eidos_evidence=eid,
        is_mock=True,
    )

    assert resp["decision"] == TrustDecision.DENY.value
    assert ReasonCode.MOCK_EVIDENCE_REJECTED_IN_PROD.value in resp["reason_codes"]
