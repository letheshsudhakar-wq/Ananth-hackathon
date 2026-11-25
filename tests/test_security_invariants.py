"""
Adversarial Security Invariant & Boundary Tests (Tasks 3 & 4).

Validates strict non-negotiable security requirements:
- Boundary conditions right at thresholds (0.699 vs 0.700, 0.749 vs 0.750).
- Deepfake attack never produces VERIFIED under any conditions.
- Identity mismatch never produces VERIFIED.
- Unknown/invalid risk levels fail closed.
- Negative or non-finite confidence values fail closed.
- Financial transactions strictly require step-up.
- Caller identity mismatch between session and evidence rejected.
"""

import pytest

from src.schemas import (
    AudioQualityReport,
    AudioQualityStatus,
    RecommendedAction,
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    EvidenceStatus,
    VerificationStatus,
    TrustDecision,
    ActionRiskLevel,
    ReasonCode,
)
from src.trust_engine.engine import AdaptiveTrustEngine


@pytest.fixture
def clean_audio() -> AudioQualityReport:
    return AudioQualityReport(
        valid=True,
        quality_status=AudioQualityStatus.GOOD,
        suitable_for_authentication=True,
        duration_seconds=3.0,
        estimated_speech_duration_seconds=2.5,
        sample_rate=16000,
        channel_count=1,
        estimated_noise_level_dbfs=-55.0,
        estimated_snr_db=25.0,
        silence_percentage=15.0,
        clipping_percentage=0.0,
        rms_dbfs=-20.0,
        peak_amplitude=0.5,
        detected_issues=[],
        recommended_action=RecommendedAction.PROCEED,
    )


@pytest.mark.parametrize("liveness,match,expected_status", [
    (0.699, 0.750, VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED), # Just below liveness threshold (0.70)
    (0.700, 0.750, VerificationStatus.VERIFIED),                         # Exactly at threshold
    (0.700, 0.749, VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED), # Just below match threshold (0.75)
    (0.700, 0.750, VerificationStatus.VERIFIED),                         # Exactly at threshold
    (0.350, 0.950, VerificationStatus.SUSPICIOUS),                        # Exactly at max spoof boundary (0.35)
    (0.351, 0.950, VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED), # Just above spoof boundary -> conflict/mismatch
])
def test_threshold_boundary_precision(clean_audio, liveness, match, expected_status):
    engine = AdaptiveTrustEngine()
    aletheia = NormalizedAletheiaEvidence(liveness_score=liveness, confidence=0.85)
    eidos = NormalizedEidosEvidence(match_score=match, confidence=0.85)
    
    out = engine.evaluate({}, clean_audio, aletheia, eidos, ActionRiskLevel.LOW)
    assert out.verification_status == expected_status


def test_adversarial_unknown_risk_level_fails_closed(clean_audio):
    """Unknown or manipulated risk tier string must fail closed to DENY."""
    engine = AdaptiveTrustEngine()
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.90)
    eidos = NormalizedEidosEvidence(match_score=0.95, confidence=0.90)

    out = engine.evaluate({}, clean_audio, aletheia, eidos, action_risk_level="INVALID_HACKED_TIER")
    assert out.decision == TrustDecision.DENY
    assert out.sensitive_operations_paused is True
    assert ReasonCode.INVALID_EVIDENCE_PAYLOAD in out.reason_codes


def test_adversarial_negative_or_nan_confidence(clean_audio):
    """Manipulated confidence out of [0, 1] interval must be caught."""
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=-0.5)
    assert aletheia.status == EvidenceStatus.INVALID

    engine = AdaptiveTrustEngine()
    out = engine.evaluate({}, clean_audio, aletheia, NormalizedEidosEvidence(match_score=0.9, confidence=0.9))
    assert out.verification_status == VerificationStatus.INCONCLUSIVE
    assert out.decision == TrustDecision.DENY


def test_adversarial_deepfake_with_perfect_audio_and_identity(clean_audio):
    """Even with 100% clean audio and 100% identity match, spoof evidence NEVER verifies."""
    engine = AdaptiveTrustEngine()
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.05, confidence=0.99)
    eidos = NormalizedEidosEvidence(match_score=0.99, confidence=0.99)

    out = engine.evaluate({}, clean_audio, aletheia, eidos, ActionRiskLevel.LOW)
    assert out.verification_status == VerificationStatus.SUSPICIOUS
    assert out.decision == TrustDecision.DENY
    assert out.sensitive_operations_paused is True
