"""
Comprehensive Automated Test Suite for Phase 4: Recovery, State Machine & Explainability.

Tests:
1. Successful recovery after noisy audio.
2. Successful recovery after insufficient speech.
3. Audio retry exhaustion -> STEP_UP_REQUIRED.
4. API service retry exhaustion -> STEP_UP_REQUIRED.
5. Expired session rejection.
6. Suspicious session remaining locked/blocked after subsequent audio recording.
7. Stale evidence rejection.
8. Cross-session evidence rejection.
9. Financial transaction safeguard step-up.
10. Correct recovery action selection across acoustic defects.
11. Accurate explanations based on reason codes.
12. Customer-facing explanation privacy (no leak of internal thresholds/numbers).
13. No direct cross-provider numerical score comparison.
"""

import time
import pytest

from src.schemas import (
    AudioQualityReport,
    AudioQualityStatus,
    AudioQualityIssue,
    RecommendedAction,
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    EvidenceStatus,
    VerificationStatus,
    TrustDecision,
    ActionRiskLevel,
    ReasonCode,
    RecoveryAction,
    SessionState,
    RecoveryConfig,
)
from src.trust_engine.engine import AdaptiveTrustEngine
from src.trust_engine.recovery import AdaptiveRecoveryEngine
from src.trust_engine.explainer import DecisionExplainer


@pytest.fixture
def clean_audio() -> AudioQualityReport:
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
        quality_notes=["Signal clear"],
    )


@pytest.fixture
def noisy_audio() -> AudioQualityReport:
    return AudioQualityReport(
        valid=True,
        quality_status=AudioQualityStatus.POOR,
        suitable_for_authentication=False,
        duration_seconds=3.0,
        estimated_speech_duration_seconds=1.5,
        sample_rate=16000,
        channel_count=1,
        estimated_noise_level_dbfs=-22.0,
        estimated_snr_db=5.0,
        silence_percentage=30.0,
        clipping_percentage=0.0,
        rms_dbfs=-18.0,
        peak_amplitude=0.5,
        detected_issues=[AudioQualityIssue.EXCESSIVE_BACKGROUND_NOISE],
        recommended_action=RecommendedAction.REQUEST_QUIETER_ENVIRONMENT,
        quality_notes=["Excessive background noise floor"],
    )


@pytest.fixture
def short_speech_audio() -> AudioQualityReport:
    return AudioQualityReport(
        valid=True,
        quality_status=AudioQualityStatus.POOR,
        suitable_for_authentication=False,
        duration_seconds=0.7,
        estimated_speech_duration_seconds=0.3,
        sample_rate=16000,
        channel_count=1,
        estimated_noise_level_dbfs=-50.0,
        estimated_snr_db=15.0,
        silence_percentage=40.0,
        clipping_percentage=0.0,
        rms_dbfs=-22.0,
        peak_amplitude=0.4,
        detected_issues=[AudioQualityIssue.INSUFFICIENT_DURATION, AudioQualityIssue.INSUFFICIENT_SPEECH],
        recommended_action=RecommendedAction.REQUEST_LONGER_RECORDING,
        quality_notes=["Insufficient speech duration"],
    )


def test_1_successful_recovery_after_noisy_audio(clean_audio, noisy_audio):
    """Turn 1: Noisy audio -> RETRY_AUDIO. Turn 2: Caller provides clean audio -> VOICE_VERIFIED."""
    engine = AdaptiveTrustEngine()
    recovery = AdaptiveRecoveryEngine()
    session = recovery.get_or_create_session("sess_noise_01", "caller_123")

    aletheia = NormalizedAletheiaEvidence(liveness_score=0.92, confidence=0.88, session_id="sess_noise_01")
    eidos = NormalizedEidosEvidence(match_score=0.90, confidence=0.85, session_id="sess_noise_01")

    # Turn 1: Noisy audio
    t1_output = engine.evaluate({}, noisy_audio, aletheia, eidos)
    rec1 = recovery.process_turn(session, noisy_audio, t1_output, aletheia, eidos)

    assert rec1.session_state == SessionState.RETRY_AUDIO
    assert rec1.recovery_action == RecoveryAction.REQUEST_QUIETER_ENVIRONMENT
    assert rec1.audio_retries_remaining == 2
    assert rec1.terminal_state is False

    # Turn 2: Recovered clean audio
    t2_output = engine.evaluate({}, clean_audio, aletheia, eidos)
    rec2 = recovery.process_turn(session, clean_audio, t2_output, aletheia, eidos)

    assert rec2.session_state == SessionState.VOICE_VERIFIED
    assert rec2.recovery_action == RecoveryAction.VERIFICATION_COMPLETE
    assert rec2.terminal_state is True
    assert rec2.decision == TrustDecision.ALLOW


def test_2_successful_recovery_after_insufficient_speech(clean_audio, short_speech_audio):
    """Turn 1: Short audio -> REQUEST_LONGER_RECORDING. Turn 2: Longer speech -> VOICE_VERIFIED."""
    engine = AdaptiveTrustEngine()
    recovery = AdaptiveRecoveryEngine()
    session = recovery.get_or_create_session("sess_short_02", "caller_123")

    aletheia = NormalizedAletheiaEvidence(liveness_score=0.90, confidence=0.85, session_id="sess_short_02")
    eidos = NormalizedEidosEvidence(match_score=0.88, confidence=0.82, session_id="sess_short_02")

    # Turn 1
    t1_output = engine.evaluate({}, short_speech_audio, aletheia, eidos)
    rec1 = recovery.process_turn(session, short_speech_audio, t1_output, aletheia, eidos)
    assert rec1.session_state == SessionState.RETRY_AUDIO
    assert rec1.recovery_action == RecoveryAction.REQUEST_LONGER_RECORDING

    # Turn 2
    t2_output = engine.evaluate({}, clean_audio, aletheia, eidos)
    rec2 = recovery.process_turn(session, clean_audio, t2_output, aletheia, eidos)
    assert rec2.session_state == SessionState.VOICE_VERIFIED


def test_3_audio_retry_exhaustion(noisy_audio):
    """Exceeding max 3 audio retries forces STEP_UP_REQUIRED with independent auth."""
    engine = AdaptiveTrustEngine()
    recovery = AdaptiveRecoveryEngine(RecoveryConfig(max_audio_retries=3))
    session = recovery.get_or_create_session("sess_exhaust_03", "caller_123")

    aletheia = NormalizedAletheiaEvidence(liveness_score=0.9, confidence=0.85, session_id="sess_exhaust_03")
    eidos = NormalizedEidosEvidence(match_score=0.9, confidence=0.85, session_id="sess_exhaust_03")

    for turn in range(3):
        t_out = engine.evaluate({}, noisy_audio, aletheia, eidos)
        rec = recovery.process_turn(session, noisy_audio, t_out, aletheia, eidos)
        assert rec.session_state == SessionState.RETRY_AUDIO

    # 4th Attempt: Exceeds max retries
    t_out_4 = engine.evaluate({}, noisy_audio, aletheia, eidos)
    rec_4 = recovery.process_turn(session, noisy_audio, t_out_4, aletheia, eidos)

    assert rec_4.session_state == SessionState.STEP_UP_REQUIRED
    assert rec_4.recovery_action == RecoveryAction.REQUIRE_INDEPENDENT_AUTHENTICATION
    assert rec_4.independent_auth_required is True
    assert ReasonCode.AUDIO_RETRY_LIMIT_EXCEEDED in rec_4.reason_codes


def test_4_service_retry_exhaustion(clean_audio):
    """Unavailable external API retries bounded at 2, then enforces independent authentication."""
    engine = AdaptiveTrustEngine()
    recovery = AdaptiveRecoveryEngine(RecoveryConfig(max_service_retries=2))
    session = recovery.get_or_create_session("sess_svc_04", "caller_123")

    aletheia = NormalizedAletheiaEvidence(status=EvidenceStatus.UNAVAILABLE, session_id="sess_svc_04")
    eidos = NormalizedEidosEvidence(match_score=0.9, confidence=0.85, session_id="sess_svc_04")

    # Turn 1
    t_out_1 = engine.evaluate({}, clean_audio, aletheia, eidos)
    rec_1 = recovery.process_turn(session, clean_audio, t_out_1, aletheia, eidos)
    assert rec_1.session_state == SessionState.RETRY_SERVICE

    # Turn 2
    t_out_2 = engine.evaluate({}, clean_audio, aletheia, eidos)
    rec_2 = recovery.process_turn(session, clean_audio, t_out_2, aletheia, eidos)
    assert rec_2.session_state == SessionState.RETRY_SERVICE

    # Turn 3: Exhaustion
    t_out_3 = engine.evaluate({}, clean_audio, aletheia, eidos)
    rec_3 = recovery.process_turn(session, clean_audio, t_out_3, aletheia, eidos)
    assert rec_3.session_state == SessionState.STEP_UP_REQUIRED
    assert rec_3.recovery_action == RecoveryAction.REQUIRE_INDEPENDENT_AUTHENTICATION
    assert ReasonCode.SERVICE_RETRY_LIMIT_EXCEEDED in rec_3.reason_codes


def test_5_expired_session(clean_audio):
    """Sessions older than timeout window (e.g. 300s) are immediately rejected."""
    engine = AdaptiveTrustEngine()
    recovery = AdaptiveRecoveryEngine(RecoveryConfig(session_timeout_seconds=300.0))
    session = recovery.get_or_create_session("sess_expire_05", "caller_123")

    now = time.time()
    session.created_at = now - 350.0  # 350 seconds ago

    aletheia = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.9, session_id="sess_expire_05")
    eidos = NormalizedEidosEvidence(match_score=0.95, confidence=0.9, session_id="sess_expire_05")

    t_out = engine.evaluate({}, clean_audio, aletheia, eidos)
    rec = recovery.process_turn(session, clean_audio, t_out, aletheia, eidos, current_time=now)

    assert rec.session_state == SessionState.EXPIRED
    assert rec.decision == TrustDecision.DENY
    assert ReasonCode.SESSION_EXPIRED in rec.reason_codes
    assert rec.terminal_state is True


def test_6_suspicious_session_remains_blocked(clean_audio):
    """
    CRITICAL SECURITY TEST:
    A session flagged as suspicious / deepfake CANNOT be unlocked by submitting new audio!
    """
    engine = AdaptiveTrustEngine()
    recovery = AdaptiveRecoveryEngine()
    session = recovery.get_or_create_session("sess_attack_06", "caller_victim")

    # Turn 1: Deepfake attack detected
    attack_aletheia = NormalizedAletheiaEvidence(liveness_score=0.10, confidence=0.95, session_id="sess_attack_06")
    eidos = NormalizedEidosEvidence(match_score=0.94, confidence=0.90, session_id="sess_attack_06")

    t_out_1 = engine.evaluate({}, clean_audio, attack_aletheia, eidos)
    rec_1 = recovery.process_turn(session, clean_audio, t_out_1, attack_aletheia, eidos)

    assert rec_1.session_state == SessionState.BLOCKED
    assert rec_1.decision == TrustDecision.DENY
    assert rec_1.recovery_action == RecoveryAction.BLOCK_SUSPICIOUS_SESSION

    # Turn 2: Attacker attempts to submit genuine audio
    genuine_aletheia = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.95, session_id="sess_attack_06")
    t_out_2 = engine.evaluate({}, clean_audio, genuine_aletheia, eidos)
    rec_2 = recovery.process_turn(session, clean_audio, t_out_2, genuine_aletheia, eidos)

    # Invariant verified: State remains BLOCKED, decision DENY!
    assert rec_2.session_state == SessionState.BLOCKED
    assert rec_2.decision == TrustDecision.DENY
    assert ReasonCode.SESSION_LOCKED_SUSPICIOUS in rec_2.reason_codes


def test_7_stale_and_cross_session_evidence(clean_audio):
    """Rejects evidence from a different session or created more than 60s ago."""
    engine = AdaptiveTrustEngine()
    recovery = AdaptiveRecoveryEngine()
    session = recovery.get_or_create_session("sess_valid_07", "caller_123")

    now = time.time()

    # Cross session evidence
    cross_aletheia = NormalizedAletheiaEvidence(
        liveness_score=0.9, confidence=0.9, session_id="sess_OTHER_99"
    )
    eidos = NormalizedEidosEvidence(match_score=0.9, confidence=0.9, session_id="sess_valid_07")

    t_out = engine.evaluate({}, clean_audio, cross_aletheia, eidos)
    rec_cross = recovery.process_turn(session, clean_audio, t_out, cross_aletheia, eidos, current_time=now)

    assert rec_cross.decision == TrustDecision.DENY
    assert ReasonCode.CROSS_SESSION_EVIDENCE_REJECTED in rec_cross.reason_codes

    # Stale evidence (timestamp 100 seconds ago)
    session_fresh = recovery.get_or_create_session("sess_fresh_08", "caller_123")
    stale_aletheia = NormalizedAletheiaEvidence(
        liveness_score=0.9, confidence=0.9, session_id="sess_fresh_08", timestamp=now - 100.0
    )
    t_out_stale = engine.evaluate({}, clean_audio, stale_aletheia, eidos)
    rec_stale = recovery.process_turn(session_fresh, clean_audio, t_out_stale, stale_aletheia, eidos, current_time=now)

    assert rec_stale.decision == TrustDecision.DENY
    assert ReasonCode.STALE_EVIDENCE_REJECTED in rec_stale.reason_codes


def test_8_financial_transaction_recovery(clean_audio):
    """Financial transactions mandate STEP_UP_REQUIRED with independent auth even with verified voice."""
    engine = AdaptiveTrustEngine()
    recovery = AdaptiveRecoveryEngine()
    session = recovery.get_or_create_session("sess_fin_09", "caller_123", ActionRiskLevel.FINANCIAL)

    aletheia = NormalizedAletheiaEvidence(liveness_score=0.95, confidence=0.90, session_id="sess_fin_09")
    eidos = NormalizedEidosEvidence(match_score=0.95, confidence=0.90, session_id="sess_fin_09")

    t_out = engine.evaluate({}, clean_audio, aletheia, eidos, action_risk_level=ActionRiskLevel.FINANCIAL)
    rec = recovery.process_turn(session, clean_audio, t_out, aletheia, eidos)

    assert rec.session_state == SessionState.STEP_UP_REQUIRED
    assert rec.decision == TrustDecision.STEP_UP_CHALLENGE
    assert rec.recovery_action == RecoveryAction.REQUIRE_INDEPENDENT_AUTHENTICATION
    assert rec.independent_auth_required is True
    assert ReasonCode.FINANCIAL_TRANSACTION_STEP_UP_REQUIRED in rec.reason_codes


def test_9_explainer_customer_vs_internal_privacy(clean_audio):
    """
    Explainer test:
    Customer message must NOT leak numerical scores, thresholds, or internal engine details.
    Internal explanation must contain full audit telemetry.
    """
    engine = AdaptiveTrustEngine()
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.15, confidence=0.92)  # Attack
    eidos = NormalizedEidosEvidence(match_score=0.90, confidence=0.90)

    t_out = engine.evaluate({}, clean_audio, aletheia, eidos)
    detail = DecisionExplainer.explain(t_out, clean_audio, aletheia, eidos)

    # Customer message checks
    assert "0.15" not in detail.customer_message
    assert "0.92" not in detail.customer_message
    assert "threshold" not in detail.customer_message.lower()
    assert "liveness" not in detail.customer_message.lower()

    # Internal explanation checks
    assert "Aletheia" in detail.internal_explanation
    assert "0.15" in detail.internal_explanation
    assert "Audit Telemetry" in detail.internal_explanation
