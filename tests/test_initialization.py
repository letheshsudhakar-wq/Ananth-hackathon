"""
Basic import and schema validation tests (Phase 1).
"""

import pytest
import numpy as np

from src.schemas import (
    AudioAssessmentInput,
    AudioQualityReport,
    AudioQualityStatus,
    MockVerificationEvidence,
    TrustDecision,
    TrustEngineOutput,
    ActionRiskLevel,
    RecommendedAction,
    VerificationStatus,
    ReasonCode,
)
from src.audio_intelligence.assessor import AudioQualityAssessor
from src.trust_engine.engine import AdaptiveTrustEngine
from src.trust_engine.mock_data import MockDataFactory


def test_schema_instantiation_and_serialization():
    """Verify schemas can be instantiated and serialized to dict cleanly."""
    report = AudioQualityReport(
        valid=True,
        quality_status=AudioQualityStatus.GOOD,
        suitable_for_authentication=True,
        duration_seconds=3.21,
        estimated_speech_duration_seconds=2.8,
        sample_rate=16000,
        channel_count=1,
        estimated_noise_level_dbfs=-50.2,
        estimated_snr_db=25.43,
        silence_percentage=12.5,
        clipping_percentage=0.0,
        rms_dbfs=-22.0,
        peak_amplitude=0.6,
        detected_issues=[],
        recommended_action=RecommendedAction.PROCEED,
        quality_notes=["Signal clean"],
    )

    data = report.to_dict()
    assert data["quality_status"] == "GOOD"
    assert data["estimated_snr_db"] == 25.43
    assert data["suitable_for_authentication"] is True

    decision = TrustEngineOutput(
        verification_status=VerificationStatus.VERIFIED,
        decision=TrustDecision.ALLOW,
        action_risk_level=ActionRiskLevel.HIGH,
        evidence_completeness=1.0,
        conflicting_evidence=False,
        confidence_indicator=0.8888,
        reason_codes=[ReasonCode.VOICE_AND_IDENTITY_VERIFIED],
        explanation="Test explanation",
        sensitive_operations_paused=False,
        independent_auth_required=False,
        audio_degradation_detected=False,
        composite_trust_score=0.91234,
        confidence_level=0.8888,
        risk_tier=ActionRiskLevel.HIGH,
    )

    dec_dict = decision.to_dict()
    assert dec_dict["decision"] == "ALLOW"
    assert dec_dict["composite_trust_score"] == 0.912


def test_audio_assessor_baseline():
    """Test AudioQualityAssessor baseline response."""
    assessor = AudioQualityAssessor()

    # Empty array test
    empty_report = assessor.assess_array(np.array([], dtype=np.float32), 16000)
    assert empty_report.quality_status == AudioQualityStatus.INVALID
    assert empty_report.suitable_for_authentication is False

    # Mock audio signal (1 second of synthetic sine wave)
    sample_rate = 16000
    t = np.linspace(0, 1.0, sample_rate, endpoint=False)
    sine_wave = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    report = assessor.assess_array(sine_wave, sample_rate)
    assert report.valid is True
    assert report.duration_seconds == 1.0


def test_trust_engine_security_rule_poor_audio():
    """
    CRITICAL SECURITY RULE:
    Never weaken authentication requirements because of poor audio quality.
    If audio is degraded/unusable, it must reject/retry rather than bypassing checks.
    """
    engine = AdaptiveTrustEngine()
    evidence, audio_report = MockDataFactory.get_unusable_audio_caller()

    result = engine.evaluate(evidence, audio_report)
    assert result.decision == TrustDecision.RETRY_AUDIO
    assert result.audio_degradation_detected is True
    assert "cannot be weakened or bypassed" in result.explanation


def test_mock_data_scenarios():
    """Verify that all mock test scenarios can be generated deterministically."""
    clean_ev, clean_aud = MockDataFactory.get_clean_legitimate_caller()
    assert clean_aud.quality_status == AudioQualityStatus.GOOD

    noisy_ev, noisy_aud = MockDataFactory.get_noisy_legitimate_caller()
    assert noisy_aud.quality_status == AudioQualityStatus.MODERATE

    spoof_ev, spoof_aud = MockDataFactory.get_deepfake_attack_caller()
    assert spoof_ev.aletheia_liveness_score < 0.20
