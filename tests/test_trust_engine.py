"""
Deterministic automated test suite for Phase 3 Adaptive Trust Engine.

Covers:
1. Genuine matching caller (VERIFIED, ALLOW).
2. Identity mismatch (ADDITIONAL_VERIFICATION_REQUIRED, STEP_UP_CHALLENGE).
3. Deepfake with matching identity (SUSPICIOUS, DENY).
4. Poor audio with positive API results (ADDITIONAL_VERIFICATION_REQUIRED, RETRY_AUDIO).
5. Poor audio with credible attack evidence (SUSPICIOUS, DENY - attack escalation invariant).
6. Missing Aletheia response (INCONCLUSIVE, STEP_UP_CHALLENGE).
7. Missing Eidos response (INCONCLUSIVE, STEP_UP_CHALLENGE).
8. Both APIs unavailable (INCONCLUSIVE, STEP_UP_CHALLENGE).
9. Low-confidence results (ADDITIONAL_VERIFICATION_REQUIRED, STEP_UP_CHALLENGE).
10. Conflicting results: genuine audio but mismatch; divergence delta.
11. Invalid scores: out of [0, 1] range.
12. NaN and infinity inputs.
13. High-risk / financial operations safeguard (voice alone cannot authorize funds).
14. Mock evidence rejected in production mode.
15. Authentication threshold non-downgrade.
"""

import pytest
import numpy as np

from src.schemas import (
    AudioQualityReport,
    AudioQualityStatus,
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    EvidenceStatus,
    VerificationStatus,
    TrustDecision,
    ActionRiskLevel,
    ReasonCode,
    RecommendedAction,
    MockVerificationEvidence,
)
from src.trust_engine.engine import AdaptiveTrustEngine


@pytest.fixture
def clean_audio_report() -> AudioQualityReport:
    """Fixture providing clean, verified audio quality."""
    return AudioQualityReport(
        valid=True,
        quality_status=AudioQualityStatus.GOOD,
        suitable_for_authentication=True,
        duration_seconds=3.5,
        estimated_speech_duration_seconds=2.8,
        sample_rate=16000,
        channel_count=1,
        estimated_noise_level_dbfs=-55.0,
        estimated_snr_db=25.0,
        silence_percentage=20.0,
        clipping_percentage=0.0,
        rms_dbfs=-20.0,
        peak_amplitude=0.6,
        detected_issues=[],
        recommended_action=RecommendedAction.PROCEED,
    )


@pytest.fixture
def poor_audio_report() -> AudioQualityReport:
    """Fixture providing degraded/unusable audio quality."""
    return AudioQualityReport(
        valid=True,
        quality_status=AudioQualityStatus.POOR,
        suitable_for_authentication=False,
        duration_seconds=0.8,
        estimated_speech_duration_seconds=0.2,
        sample_rate=16000,
        channel_count=1,
        estimated_noise_level_dbfs=-20.0,
        estimated_snr_db=4.0,
        silence_percentage=75.0,
        clipping_percentage=8.0,
        rms_dbfs=-15.0,
        peak_amplitude=1.0,
        detected_issues=[],
        recommended_action=RecommendedAction.REQUEST_FRESH_RECORDING,
    )


def test_1_genuine_matching_caller(clean_audio_report):
    """Scenario 1: Clean audio, high liveness, high voice match -> VERIFIED, ALLOW."""
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.90)
    eidos = NormalizedEidosEvidence(match_score=0.92, confidence=0.88)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
        action_risk_level=ActionRiskLevel.LOW,
    )

    assert outcome.verification_status == VerificationStatus.VERIFIED
    assert outcome.decision == TrustDecision.ALLOW
    assert outcome.sensitive_operations_paused is False
    assert ReasonCode.VOICE_AND_IDENTITY_VERIFIED in outcome.reason_codes


def test_2_identity_mismatch(clean_audio_report):
    """Scenario 2: Real human voice (liveness=0.95) but identity mismatch (eidos=0.25)."""
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.92)
    eidos = NormalizedEidosEvidence(match_score=0.25, confidence=0.90)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
        action_risk_level=ActionRiskLevel.MEDIUM,
    )

    assert outcome.verification_status == VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED
    assert outcome.decision == TrustDecision.STEP_UP_CHALLENGE
    assert outcome.conflicting_evidence is True
    assert outcome.sensitive_operations_paused is True
    assert ReasonCode.SPEAKER_IDENTITY_MISMATCH in outcome.reason_codes


def test_3_deepfake_with_matching_identity(clean_audio_report):
    """Scenario 3: Synthetic deepfake attack with victim voice timbre match."""
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.10, confidence=0.95)  # Synthetic
    eidos = NormalizedEidosEvidence(match_score=0.94, confidence=0.92)           # Timbre match

    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
        action_risk_level=ActionRiskLevel.HIGH,
    )

    assert outcome.verification_status == VerificationStatus.SUSPICIOUS
    assert outcome.decision == TrustDecision.DENY
    assert outcome.sensitive_operations_paused is True
    assert ReasonCode.CREDIBLE_DEEPFAKE_DETECTED in outcome.reason_codes


def test_4_poor_audio_with_positive_api_results(poor_audio_report):
    """Scenario 4: High biometric scores but inadequate audio quality -> RETRY_AUDIO."""
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.90)
    eidos = NormalizedEidosEvidence(match_score=0.95, confidence=0.90)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=poor_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
        action_risk_level=ActionRiskLevel.LOW,
    )

    assert outcome.verification_status == VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED
    assert outcome.decision == TrustDecision.RETRY_AUDIO
    assert outcome.sensitive_operations_paused is True
    assert outcome.audio_degradation_detected is True
    assert ReasonCode.POOR_AUDIO_QUALITY in outcome.reason_codes


def test_5_poor_audio_with_credible_attack_escalation(poor_audio_report):
    """
    Scenario 5: Invariant check - Credible attack MUST NOT be masked by poor audio.
    If deepfake detected, it escalates to SUSPICIOUS/DENY, not RETRY_AUDIO.
    """
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.15, confidence=0.92)  # Attack
    eidos = NormalizedEidosEvidence(match_score=0.30, confidence=0.70)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=poor_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
    )

    assert outcome.verification_status == VerificationStatus.SUSPICIOUS
    assert outcome.decision == TrustDecision.DENY
    assert ReasonCode.CREDIBLE_DEEPFAKE_DETECTED in outcome.reason_codes


def test_6_missing_aletheia_response(clean_audio_report):
    """Scenario 6: Aletheia missing, Eidos passed."""
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(status=EvidenceStatus.MISSING)
    eidos = NormalizedEidosEvidence(match_score=0.90, confidence=0.85)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
    )

    assert outcome.verification_status == VerificationStatus.INCONCLUSIVE
    assert outcome.decision == TrustDecision.STEP_UP_CHALLENGE
    assert ReasonCode.MISSING_OR_UNAVAILABLE_EVIDENCE in outcome.reason_codes


def test_7_missing_eidos_response(clean_audio_report):
    """Scenario 7: Eidos unavailable, Aletheia passed."""
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.90, confidence=0.85)
    eidos = NormalizedEidosEvidence(status=EvidenceStatus.UNAVAILABLE)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
    )

    assert outcome.verification_status == VerificationStatus.INCONCLUSIVE
    assert outcome.decision == TrustDecision.STEP_UP_CHALLENGE


def test_8_both_apis_unavailable(clean_audio_report):
    """Scenario 8: Both APIs unavailable."""
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(status=EvidenceStatus.UNAVAILABLE)
    eidos = NormalizedEidosEvidence(status=EvidenceStatus.UNAVAILABLE)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
    )

    assert outcome.verification_status == VerificationStatus.INCONCLUSIVE
    assert outcome.decision == TrustDecision.STEP_UP_CHALLENGE


def test_9_low_confidence_results(clean_audio_report):
    """Scenario 9: High biometric scores but low confidence (< 0.65)."""
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.90, confidence=0.45)
    eidos = NormalizedEidosEvidence(match_score=0.90, confidence=0.85)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
    )

    assert outcome.verification_status == VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED
    assert outcome.decision == TrustDecision.STEP_UP_CHALLENGE
    assert ReasonCode.LOW_CONFIDENCE_EVIDENCE in outcome.reason_codes


def test_10_divergent_conflicting_results(clean_audio_report):
    """Scenario 10: Scores with high delta (> 0.45 divergence)."""
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.85, confidence=0.80)
    eidos = NormalizedEidosEvidence(match_score=0.35, confidence=0.80)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
    )

    assert outcome.conflicting_evidence is True
    assert outcome.verification_status == VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED
    assert outcome.decision == TrustDecision.STEP_UP_CHALLENGE


def test_11_invalid_out_of_range_scores(clean_audio_report):
    """Scenario 11: Score outside [0.0, 1.0]."""
    aletheia = NormalizedAletheiaEvidence(liveness_score=1.5, confidence=0.9)
    assert aletheia.status == EvidenceStatus.INVALID

    engine = AdaptiveTrustEngine(production_mode=False)
    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=NormalizedEidosEvidence(match_score=0.9, confidence=0.9),
    )

    assert outcome.verification_status == VerificationStatus.INCONCLUSIVE
    assert outcome.decision == TrustDecision.DENY
    assert ReasonCode.INVALID_EVIDENCE_PAYLOAD in outcome.reason_codes


def test_12_nan_and_infinity_evidence(clean_audio_report):
    """Scenario 12: NaN or Inf in scores."""
    aletheia = NormalizedAletheiaEvidence(liveness_score=float("nan"), confidence=0.9)
    assert aletheia.status == EvidenceStatus.INVALID

    eidos = NormalizedEidosEvidence(match_score=float("inf"), confidence=0.9)
    assert eidos.status == EvidenceStatus.INVALID

    engine = AdaptiveTrustEngine(production_mode=False)
    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
    )

    assert outcome.verification_status == VerificationStatus.INCONCLUSIVE
    assert outcome.decision == TrustDecision.DENY


def test_13_financial_transaction_safeguard(clean_audio_report):
    """
    Scenario 13: Strict Invariant - Voice alone CANNOT authorize financial transactions.
    Even with verified voice, financial operations enforce STEP_UP_CHALLENGE.
    """
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.90)
    eidos = NormalizedEidosEvidence(match_score=0.95, confidence=0.90)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=clean_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
        action_risk_level=ActionRiskLevel.FINANCIAL,
    )

    assert outcome.verification_status == VerificationStatus.VERIFIED
    assert outcome.decision == TrustDecision.STEP_UP_CHALLENGE
    assert outcome.independent_auth_required is True
    assert outcome.sensitive_operations_paused is True
    assert ReasonCode.FINANCIAL_TRANSACTION_STEP_UP_REQUIRED in outcome.reason_codes


def test_14_mock_evidence_rejected_in_production_mode(clean_audio_report):
    """Scenario 14: Mock evidence passed when production_mode=True is denied."""
    engine = AdaptiveTrustEngine(production_mode=True)
    mock_ev = MockVerificationEvidence(
        caller_id="test_user",
        aletheia_liveness_score=0.95,
        aletheia_confidence=0.90,
        eidos_voice_match_score=0.95,
        eidos_confidence=0.90,
        is_mock=True,
    )

    outcome = engine.evaluate(
        evidence=mock_ev,
        audio_quality=clean_audio_report,
    )

    assert outcome.decision == TrustDecision.DENY
    assert ReasonCode.MOCK_EVIDENCE_REJECTED_IN_PROD in outcome.reason_codes


def test_15_authentication_threshold_non_downgrade(poor_audio_report):
    """
    Scenario 15: Security Invariant - Authentication threshold must never be downgraded
    due to poor audio quality.
    """
    engine = AdaptiveTrustEngine(production_mode=False)
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.72, confidence=0.70)
    eidos = NormalizedEidosEvidence(match_score=0.76, confidence=0.70)

    outcome = engine.evaluate(
        evidence={},
        audio_quality=poor_audio_report,
        aletheia_evidence=aletheia,
        eidos_evidence=eidos,
        action_risk_level=ActionRiskLevel.LOW,
    )

    # Must be RETRY_AUDIO, NEVER ALLOW
    assert outcome.decision == TrustDecision.RETRY_AUDIO
    assert outcome.decision != TrustDecision.ALLOW
    assert outcome.sensitive_operations_paused is True
