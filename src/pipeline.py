"""
Unified Two-Stage Integration Pipeline for ANANTH (Member 3).

Provides a clean, unified public interface that Member 2 can import.
Supports:
- Audio file paths, raw bytes, BytesIO, or NumPy arrays
- Normalized Aletheia authenticity evidence
- Normalized Eidos speaker identity evidence
- Backend-controlled action risk levels
- Multi-turn state machine session binding

Two-Stage Workflow:
- Stage A (pre-flight): validate_and_assess_audio()
  Checks acoustic quality and provider submission eligibility without calling external APIs.
- Stage B (decision & recovery): evaluate_trust_and_recover()
  Accepts normalized provider evidence, evaluates trust, updates session state,
  and returns a unified, JSON-serializable payload ready for Member 1 (Frontend).
"""

import time
from typing import Union, Optional, Dict, Any
import io
import numpy as np

from src.audio_intelligence import analyze_audio
from src.trust_engine.engine import AdaptiveTrustEngine
from src.trust_engine.recovery import (
    AdaptiveRecoveryEngine,
    AuthenticationSession,
)
from src.trust_engine.explainer import DecisionExplainer
from src.schemas import (
    AudioQualityReport,
    AudioQualityStatus,
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    EvidenceStatus,
    ActionRiskLevel,
    VerificationStatus,
    TrustDecision,
    ReasonCode,
    RecoveryAction,
    SessionState,
    StructuredRecoveryOutput,
    ProviderApiDurationLimits,
)


class AnanthPipeline:
    """
    Unified Integration Pipeline facade for ANANTH voice authentication.
    Member 2 imports and initializes this class once in the backend lifecycle.
    """

    def __init__(
        self,
        production_mode: bool = False,
        provider_limits: Optional[ProviderApiDurationLimits] = None,
    ):
        self.production_mode = production_mode
        self.provider_limits = provider_limits or ProviderApiDurationLimits()
        self.trust_engine = AdaptiveTrustEngine(production_mode=production_mode)
        self.recovery_engine = AdaptiveRecoveryEngine()

    def get_or_create_session(
        self,
        session_id: str,
        caller_id: str,
        action_risk_level: ActionRiskLevel = ActionRiskLevel.MEDIUM,
    ) -> AuthenticationSession:
        """Retrieves or creates a backend-controlled authentication session."""
        return self.recovery_engine.get_or_create_session(
            session_id=session_id,
            caller_id=caller_id,
            action_risk_level=action_risk_level,
        )

    # --------------------------------------------------------------------------
    # STAGE A: Audio Pre-Flight Assessment & Provider Eligibility
    # --------------------------------------------------------------------------

    def stage_a_assess_audio(
        self,
        audio_input: Union[str, bytes, io.BytesIO, np.ndarray],
        sample_rate: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Stage A: Validates input audio, extracts acoustic features, and determines
        whether the sample meets both physical quality and provider duration constraints.

        Returns a dictionary containing:
        - valid: bool
        - suitable_for_authentication: bool
        - eligible_for_aletheia: bool
        - eligible_for_eidos: bool
        - audio_quality: AudioQualityReport.to_dict()
        - recommended_action: str
        """
        t0 = time.perf_counter()
        report: AudioQualityReport = analyze_audio(audio_input=audio_input, sample_rate=sample_rate)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        # Check provider duration limits (decoupled from physical quality)
        dur = report.duration_seconds
        eligible_aletheia = report.suitable_for_authentication and (
            self.provider_limits.aletheia_min_duration_seconds <= dur <= self.provider_limits.aletheia_max_duration_seconds
        )
        eligible_eidos = report.suitable_for_authentication and (
            self.provider_limits.eidos_min_duration_seconds <= dur <= self.provider_limits.eidos_max_duration_seconds
        )

        return {
            "valid": report.valid,
            "suitable_for_authentication": report.suitable_for_authentication,
            "eligible_for_aletheia": eligible_aletheia,
            "eligible_for_eidos": eligible_eidos,
            "duration_seconds": report.duration_seconds,
            "estimated_speech_duration_seconds": report.estimated_speech_duration_seconds,
            "estimated_snr_db": report.estimated_snr_db,
            "quality_status": report.quality_status.value,
            "recommended_action": report.recommended_action.value,
            "quality_notes": report.quality_notes,
            "stage_a_processing_time_ms": elapsed_ms,
            "raw_report": report,
        }

    # --------------------------------------------------------------------------
    # STAGE B: Trust Evaluation, Recovery State Machine & Explainability
    # --------------------------------------------------------------------------

    def stage_b_evaluate_and_recover(
        self,
        session_id: str,
        caller_id: str,
        audio_report: AudioQualityReport,
        aletheia_evidence: Optional[NormalizedAletheiaEvidence] = None,
        eidos_evidence: Optional[NormalizedEidosEvidence] = None,
        action_risk_level: Optional[ActionRiskLevel] = None,
        is_mock: bool = False,
    ) -> Dict[str, Any]:
        """
        Stage B: Evaluates multi-source evidence, updates session state,
        generates customer/internal explanations, and returns a unified JSON payload.
        """
        t0 = time.perf_counter()
        session = self.get_or_create_session(
            session_id=session_id,
            caller_id=caller_id,
            action_risk_level=action_risk_level or ActionRiskLevel.MEDIUM,
        )

        # In production mode, reject mock evidence immediately
        if self.production_mode and (is_mock or (aletheia_evidence and aletheia_evidence.is_mock) or (eidos_evidence and eidos_evidence.is_mock)):
            if aletheia_evidence:
                aletheia_evidence.is_mock = True
            else:
                aletheia_evidence = NormalizedAletheiaEvidence(is_mock=True, session_id=session_id)
            if eidos_evidence:
                eidos_evidence.is_mock = True
            else:
                eidos_evidence = NormalizedEidosEvidence(is_mock=True, session_id=session_id)
            is_mock = True

        # Bind session ID to evidence if not already assigned
        if aletheia_evidence and not aletheia_evidence.session_id:
            aletheia_evidence.session_id = session_id
        if eidos_evidence and not eidos_evidence.session_id:
            eidos_evidence.session_id = session_id

        # If no evidence was provided at all (e.g. Stage A caught bad audio, so no APIs were called),
        # preserve evidence as None so trust_engine handles it as audio-only evaluation
        # rather than creating MISSING evidence placeholders that trigger RETRY_SERVICE
        aletheia_to_eval = aletheia_evidence
        eidos_to_eval = eidos_evidence
        if audio_report and not audio_report.suitable_for_authentication:
            # When audio is degraded, we evaluate audio quality directly without expecting API results
            pass
        else:
            if aletheia_to_eval is None:
                aletheia_to_eval = NormalizedAletheiaEvidence(status=EvidenceStatus.MISSING, session_id=session_id)
            if eidos_to_eval is None:
                eidos_to_eval = NormalizedEidosEvidence(status=EvidenceStatus.MISSING, session_id=session_id)

        # 1. Evaluate Adaptive Trust
        trust_output = self.trust_engine.evaluate(
            evidence={"is_mock": is_mock} if is_mock else {},
            audio_quality=audio_report,
            aletheia_evidence=aletheia_to_eval,
            eidos_evidence=eidos_to_eval,
            action_risk_level=session.action_risk_level,
        )

        # 2. Process Multi-Turn Recovery Transition
        recovery_output: StructuredRecoveryOutput = self.recovery_engine.process_turn(
            session=session,
            audio_report=audio_report,
            trust_output=trust_output,
            aletheia_evidence=aletheia_to_eval,
            eidos_evidence=eidos_to_eval,
        )

        # 3. Generate Explainable Telemetry
        explanation = DecisionExplainer.explain(
            trust_output=trust_output,
            audio_report=audio_report,
            aletheia=aletheia_evidence,
            eidos=eidos_evidence,
            recovery_output=recovery_output,
        )

        total_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        # 4. Construct Member 1 (Frontend) & Member 2 (API) Unified Response
        response = {
            "session_id": session.session_id,
            "caller_id": session.caller_id,
            "attempt_number": session.attempt_number,
            "verification_status": recovery_output.verification_status.value,
            "decision": recovery_output.decision.value,
            "audio_quality": audio_report.quality_status.value,
            "estimated_speech_duration": audio_report.estimated_speech_duration_seconds,
            "estimated_snr": audio_report.estimated_snr_db,
            "evidence_summary": explanation.evidence_summary,
            "conflicting_evidence": trust_output.conflicting_evidence,
            "reason_codes": [rc.value for rc in recovery_output.reason_codes],
            "recovery_action": recovery_output.recovery_action.value,
            "customer_message": recovery_output.customer_message,
            "retries_remaining": recovery_output.audio_retries_remaining,
            "service_retries_remaining": recovery_output.service_retries_remaining,
            "session_state": recovery_output.session_state.value,
            "sensitive_operations_paused": recovery_output.sensitive_operations_paused,
            "independent_auth_required": recovery_output.independent_auth_required,
            "terminal_state": recovery_output.terminal_state,
            "processing_time_ms": total_elapsed_ms,
            "demo_mode": not self.production_mode,
            "internal_explanation": explanation.internal_explanation,
            "security_restrictions": explanation.security_restrictions,
        }

        return response
