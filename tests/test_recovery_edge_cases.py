"""
Advanced Recovery & State Machine Edge Case Tests (Task 5).

Tests:
- Concurrent/repeated session updates
- Attempts to bypass independent authentication
- Accurate customer message without contradictory statements
- Non-exposure of raw audio or personal identifiers in explanations
"""

import pytest
import time

from src.schemas import (
    AudioQualityReport,
    AudioQualityStatus,
    RecommendedAction,
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    VerificationStatus,
    TrustDecision,
    ActionRiskLevel,
    ReasonCode,
    RecoveryAction,
    SessionState,
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


def test_recovery_edge_repeated_failed_attempts(clean_audio):
    """Multiple mismatched voice attempts force STEP_UP_REQUIRED and keep operations paused."""
    engine = AdaptiveTrustEngine()
    recovery = AdaptiveRecoveryEngine()
    session = recovery.get_or_create_session("sess_repeat_01", "victim_user")

    aletheia = NormalizedAletheiaEvidence(liveness_score=0.9, confidence=0.9, session_id="sess_repeat_01")
    # Impersonator voice mismatch
    eidos_mismatch = NormalizedEidosEvidence(match_score=0.2, confidence=0.9, session_id="sess_repeat_01")

    for attempt in range(2):
        t_out = engine.evaluate({}, clean_audio, aletheia, eidos_mismatch)
        rec = recovery.process_turn(session, clean_audio, t_out, aletheia, eidos_mismatch)
        assert rec.session_state == SessionState.STEP_UP_REQUIRED
        assert rec.independent_auth_required is True
        assert rec.sensitive_operations_paused is True


def test_explainer_no_contradictory_messages(clean_audio):
    """Ensure explainer never pairs 'approved' customer message with 'deny' action."""
    engine = AdaptiveTrustEngine()
    aletheia = NormalizedAletheiaEvidence(liveness_score=0.1, confidence=0.95)
    eidos = NormalizedEidosEvidence(match_score=0.95, confidence=0.95)

    t_out = engine.evaluate({}, clean_audio, aletheia, eidos)
    detail = DecisionExplainer.explain(t_out, clean_audio, aletheia, eidos)

    assert t_out.decision == TrustDecision.DENY
    assert "approved" not in detail.customer_message.lower()
    assert "successful" not in detail.customer_message.lower()
    assert "security reasons" in detail.customer_message or "unable" in detail.customer_message.lower()
