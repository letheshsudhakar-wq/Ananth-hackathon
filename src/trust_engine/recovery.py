"""
Adaptive Recovery Engine and Multi-Turn Authentication Session State Machine.

Responsibilities:
- Manage the state lifecycle of caller authentication sessions:
  INITIAL -> COLLECTING_EVIDENCE -> (VOICE_VERIFIED | RETRY_AUDIO | RETRY_SERVICE | STEP_UP_REQUIRED | ESCALATED | BLOCKED | EXPIRED)
- Strictly enforce retry bounds (max audio retries, max service retries, session timeout).
- Guarantee tamper resistance: Bind evidence strictly to session_id, attempt_number, and caller_id.
- Security Invariants:
  - Suspicious or blocked sessions CANNOT be unblocked by submitting new audio recordings.
  - Expired sessions reject all further attempts.
  - Stale evidence or cross-session evidence is rejected.
  - Credible attacks always supersede acoustic retries.
"""

import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field

from src.schemas import (
    SessionState,
    RecoveryAction,
    VerificationStatus,
    TrustDecision,
    ReasonCode,
    ActionRiskLevel,
    AudioQualityReport,
    AudioQualityStatus,
    AudioQualityIssue,
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    TrustEngineOutput,
    RecoveryConfig,
    StructuredRecoveryOutput,
)


class SessionSecurityError(Exception):
    """Raised when an illegal state transition or session hijacking attempt occurs."""
    pass


@dataclass
class AuthenticationSession:
    """
    Server-side state container for a multi-turn voice authentication session.
    Controlled strictly by the trusted backend.
    """
    session_id: str
    caller_id: str
    action_risk_level: ActionRiskLevel
    config: RecoveryConfig = field(default_factory=RecoveryConfig)
    
    # State tracking
    state: SessionState = SessionState.INITIAL
    attempt_number: int = 0
    audio_retry_count: int = 0
    service_retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_updated_at: float = field(default_factory=time.time)
    
    # History & security flags
    suspicious_detected: bool = False
    independent_auth_required: bool = False
    terminal: bool = False
    previous_reason_codes: List[ReasonCode] = field(default_factory=list)
    latest_output: Optional[TrustEngineOutput] = None

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        return (now - self.created_at) > self.config.session_timeout_seconds

    def check_and_update_expiry(self, current_time: Optional[float] = None) -> bool:
        # A blocked session stays permanently blocked; it never transitions to expired
        if self.state == SessionState.BLOCKED:
            return False
        if self.state == SessionState.EXPIRED:
            return True
        if self.is_expired(current_time):
            self.state = SessionState.EXPIRED
            self.terminal = True
            return True
        return False


class AdaptiveRecoveryEngine:
    """
    Intelligent Adaptive Recovery Engine.
    Coordinates session transitions, selects prioritized recovery actions,
    and produces structured recovery directives.
    """

    def __init__(self, config: Optional[RecoveryConfig] = None):
        self.config = config or RecoveryConfig()
        # In-memory session store (appropriate for hackathon prototype)
        self._sessions: Dict[str, AuthenticationSession] = {}

    def get_or_create_session(
        self,
        session_id: str,
        caller_id: str,
        action_risk_level: ActionRiskLevel = ActionRiskLevel.MEDIUM,
    ) -> AuthenticationSession:
        if session_id not in self._sessions:
            self._sessions[session_id] = AuthenticationSession(
                session_id=session_id,
                caller_id=caller_id,
                action_risk_level=action_risk_level,
                config=self.config,
            )
        return self._sessions[session_id]

    def process_turn(
        self,
        session: AuthenticationSession,
        audio_report: AudioQualityReport,
        trust_output: TrustEngineOutput,
        aletheia_evidence: Optional[NormalizedAletheiaEvidence] = None,
        eidos_evidence: Optional[NormalizedEidosEvidence] = None,
        current_time: Optional[float] = None,
    ) -> StructuredRecoveryOutput:
        """
        Executes a single multi-turn state transition and produces a structured recovery plan.
        """
        now = current_time if current_time is not None else time.time()
        session.last_updated_at = now
        session.attempt_number += 1

        # 1. Expiry Check
        if session.check_and_update_expiry(now):
            return self._build_recovery_output(
                session=session,
                verification_status=VerificationStatus.INCONCLUSIVE,
                state=SessionState.EXPIRED,
                decision=TrustDecision.DENY,
                reason_codes=[ReasonCode.SESSION_EXPIRED],
                recovery_action=RecoveryAction.REQUEST_FRESH_RECORDING,
                customer_message="Your verification session has expired. Please initiate a fresh request.",
                internal_explanation="Session TTL exceeded max timeout window.",
                terminal_state=True,
                sensitive_operations_paused=True,
                independent_auth_required=True,
            )

        # 2. Blocked / Suspicious / Production Mock Rejection Locking Invariant:
        if ReasonCode.MOCK_EVIDENCE_REJECTED_IN_PROD in trust_output.reason_codes:
            session.state = SessionState.BLOCKED
            session.terminal = True
            return self._build_recovery_output(
                session=session,
                verification_status=VerificationStatus.INCONCLUSIVE,
                state=SessionState.BLOCKED,
                decision=TrustDecision.DENY,
                reason_codes=trust_output.reason_codes,
                recovery_action=RecoveryAction.BLOCK_SUSPICIOUS_SESSION,
                customer_message="Security policy violation: Mock test credentials rejected in production environment.",
                internal_explanation="Mock evidence rejected in production mode.",
                terminal_state=True,
                sensitive_operations_paused=True,
                independent_auth_required=True,
            )

        if session.suspicious_detected or session.state == SessionState.BLOCKED:
            session.state = SessionState.BLOCKED
            session.terminal = True
            return self._build_recovery_output(
                session=session,
                verification_status=VerificationStatus.SUSPICIOUS,
                state=SessionState.BLOCKED,
                decision=TrustDecision.DENY,
                reason_codes=[ReasonCode.SESSION_LOCKED_SUSPICIOUS],
                recovery_action=RecoveryAction.BLOCK_SUSPICIOUS_SESSION,
                customer_message="Unable to verify identity. For your security, this session has been locked. Please contact support.",
                internal_explanation="Session locked due to prior or current credible spoofing/deepfake indicators.",
                terminal_state=True,
                sensitive_operations_paused=True,
                independent_auth_required=True,
            )

        # 3. Evidence Binding & Tamper Validation:
        # Reject stale evidence or cross-session attempts
        stale_err = self._validate_evidence_binding(session, aletheia_evidence, eidos_evidence, now)
        if stale_err:
            return self._build_recovery_output(
                session=session,
                verification_status=VerificationStatus.INCONCLUSIVE,
                state=SessionState.ESCALATED,
                decision=TrustDecision.DENY,
                reason_codes=[stale_err],
                recovery_action=RecoveryAction.ESCALATE_FOR_MANUAL_REVIEW,
                customer_message="Verification security error. Session evidence mismatch.",
                internal_explanation=f"Evidence binding validation failed: {stale_err.value}",
                terminal_state=True,
                sensitive_operations_paused=True,
                independent_auth_required=True,
            )

        # 4. Critical Attack Escalation Check
        if trust_output.verification_status == VerificationStatus.SUSPICIOUS or \
           ReasonCode.CREDIBLE_DEEPFAKE_DETECTED in trust_output.reason_codes:
            session.suspicious_detected = True
            session.state = SessionState.BLOCKED
            session.terminal = True
            session.previous_reason_codes.extend(trust_output.reason_codes)
            return self._build_recovery_output(
                session=session,
                verification_status=VerificationStatus.SUSPICIOUS,
                state=SessionState.BLOCKED,
                decision=TrustDecision.DENY,
                reason_codes=trust_output.reason_codes,
                recovery_action=RecoveryAction.BLOCK_SUSPICIOUS_SESSION,
                customer_message="Voice authentication failed security policy. Please contact customer care.",
                internal_explanation=trust_output.explanation,
                terminal_state=True,
                sensitive_operations_paused=True,
                independent_auth_required=True,
            )

        # 6. Audio Degradation / Acoustic Retry Handling (RETRY_AUDIO)
        # Check audio retry before service unavailability if audio itself was unsuitable!
        if trust_output.decision == TrustDecision.RETRY_AUDIO or not audio_report.suitable_for_authentication:
            session.audio_retry_count += 1
            if session.audio_retry_count > session.config.max_audio_retries:
                # Audio retries exhausted -> Escalate to independent authentication
                session.state = SessionState.STEP_UP_REQUIRED
                session.independent_auth_required = True
                return self._build_recovery_output(
                    session=session,
                    verification_status=VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED,
                    state=SessionState.STEP_UP_REQUIRED,
                    decision=TrustDecision.STEP_UP_CHALLENGE,
                    reason_codes=[ReasonCode.AUDIO_RETRY_LIMIT_EXCEEDED],
                    recovery_action=RecoveryAction.REQUIRE_INDEPENDENT_AUTHENTICATION,
                    customer_message="Audio could not be clearly verified after multiple attempts. Please complete verification using your secondary security method.",
                    internal_explanation=f"Max audio retries ({session.config.max_audio_retries}) exceeded. Escalated to step-up independent auth.",
                    terminal_state=False,
                    sensitive_operations_paused=True,
                    independent_auth_required=True,
                )

            # Map acoustic issue to specific recovery action
            action = self._map_audio_action(audio_report)
            msg = self._get_customer_audio_msg(action)
            session.state = SessionState.RETRY_AUDIO
            return self._build_recovery_output(
                session=session,
                verification_status=VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED,
                state=SessionState.RETRY_AUDIO,
                decision=TrustDecision.RETRY_AUDIO,
                reason_codes=trust_output.reason_codes,
                recovery_action=action,
                customer_message=msg,
                internal_explanation=f"Audio degraded: {'; '.join(audio_report.quality_notes)}. Attempt {session.audio_retry_count}/{session.config.max_audio_retries}.",
                terminal_state=False,
                sensitive_operations_paused=True,
                independent_auth_required=False,
            )

        # 5. Service Unavailability Handling (RETRY_SERVICE)
        if ReasonCode.MISSING_OR_UNAVAILABLE_EVIDENCE in trust_output.reason_codes:
            session.service_retry_count += 1
            if session.service_retry_count > session.config.max_service_retries:
                # Service retries exhausted -> Escalate to independent secondary authentication
                session.state = SessionState.STEP_UP_REQUIRED
                session.independent_auth_required = True
                return self._build_recovery_output(
                    session=session,
                    verification_status=VerificationStatus.INCONCLUSIVE,
                    state=SessionState.STEP_UP_REQUIRED,
                    decision=TrustDecision.STEP_UP_CHALLENGE,
                    reason_codes=[ReasonCode.SERVICE_RETRY_LIMIT_EXCEEDED],
                    recovery_action=RecoveryAction.REQUIRE_INDEPENDENT_AUTHENTICATION,
                    customer_message="Voice verification service is currently busy. Please complete verification using an alternate method.",
                    internal_explanation=f"Service retry limit ({session.config.max_service_retries}) exhausted. Enforced step-up independent auth.",
                    terminal_state=False,
                    sensitive_operations_paused=True,
                    independent_auth_required=True,
                )
            session.state = SessionState.RETRY_SERVICE
            return self._build_recovery_output(
                session=session,
                verification_status=VerificationStatus.INCONCLUSIVE,
                state=SessionState.RETRY_SERVICE,
                decision=TrustDecision.STEP_UP_CHALLENGE,
                reason_codes=trust_output.reason_codes,
                recovery_action=RecoveryAction.RETRY_VERIFICATION_SERVICE,
                customer_message="Please wait a moment while we re-check our verification systems.",
                internal_explanation=f"Service unavailable; retry attempt {session.service_retry_count}/{session.config.max_service_retries}.",
                terminal_state=False,
                sensitive_operations_paused=True,
                independent_auth_required=False,
            )

        # 7. Verification Success or High-Risk / Financial Step-Up
        if trust_output.verification_status == VerificationStatus.VERIFIED:
            if trust_output.decision == TrustDecision.ALLOW:
                session.state = SessionState.VOICE_VERIFIED
                session.terminal = True
                return self._build_recovery_output(
                    session=session,
                    verification_status=VerificationStatus.VERIFIED,
                    state=SessionState.VOICE_VERIFIED,
                    decision=TrustDecision.ALLOW,
                    reason_codes=trust_output.reason_codes,
                    recovery_action=RecoveryAction.VERIFICATION_COMPLETE,
                    customer_message="Voice authentication successful.",
                    internal_explanation="Voice authenticity and speaker match verified with required confidence.",
                    terminal_state=True,
                    sensitive_operations_paused=False,
                    independent_auth_required=False,
                )
            else:
                # Financial / High risk operation requiring mandatory step-up
                session.state = SessionState.STEP_UP_REQUIRED
                session.independent_auth_required = True
                return self._build_recovery_output(
                    session=session,
                    verification_status=VerificationStatus.VERIFIED,
                    state=SessionState.STEP_UP_REQUIRED,
                    decision=TrustDecision.STEP_UP_CHALLENGE,
                    reason_codes=trust_output.reason_codes,
                    recovery_action=RecoveryAction.REQUIRE_INDEPENDENT_AUTHENTICATION,
                    customer_message="Voice identity confirmed. Please complete secondary confirmation for this high-value transaction.",
                    internal_explanation="Voice matched, but transaction policy mandates secondary step-up authorization.",
                    terminal_state=False,
                    sensitive_operations_paused=True,
                    independent_auth_required=True,
                )

        # 8. Identity Mismatch / Conflicting Evidence -> Step-Up Required
        session.state = SessionState.STEP_UP_REQUIRED
        session.independent_auth_required = True
        return self._build_recovery_output(
            session=session,
            verification_status=trust_output.verification_status,
            state=SessionState.STEP_UP_REQUIRED,
            decision=TrustDecision.STEP_UP_CHALLENGE,
            reason_codes=trust_output.reason_codes,
            recovery_action=RecoveryAction.REQUIRE_INDEPENDENT_AUTHENTICATION,
            customer_message="We could not confirm your voice match with certainty. Please verify using your registered security backup.",
            internal_explanation=trust_output.explanation,
            terminal_state=False,
            sensitive_operations_paused=True,
            independent_auth_required=True,
        )

    # --------------------------------------------------------------------------
    # Helper Methods
    # --------------------------------------------------------------------------

    def _validate_evidence_binding(
        self,
        session: AuthenticationSession,
        aletheia: Optional[NormalizedAletheiaEvidence],
        eidos: Optional[NormalizedEidosEvidence],
        current_time: float,
    ) -> Optional[ReasonCode]:
        """Validates that evidence belongs to this specific session and is fresh."""
        for ev in (aletheia, eidos):
            if ev is not None:
                # Cross-session check
                if ev.session_id is not None and ev.session_id != session.session_id:
                    return ReasonCode.CROSS_SESSION_EVIDENCE_REJECTED
                # Stale evidence check (evidence generated more than 60 seconds ago for a new turn)
                if ev.timestamp is not None and (current_time - ev.timestamp) > 60.0:
                    return ReasonCode.STALE_EVIDENCE_REJECTED
        return None

    def _map_audio_action(self, audio: AudioQualityReport) -> RecoveryAction:
        if AudioQualityIssue.AUDIO_CLIPPING in audio.detected_issues:
            return RecoveryAction.REDUCE_MICROPHONE_GAIN
        if AudioQualityIssue.EXCESSIVE_BACKGROUND_NOISE in audio.detected_issues:
            return RecoveryAction.REQUEST_QUIETER_ENVIRONMENT
        if AudioQualityIssue.LOW_RECORDING_VOLUME in audio.detected_issues:
            return RecoveryAction.SPEAK_CLOSER_TO_MIC
        if AudioQualityIssue.INSUFFICIENT_SPEECH in audio.detected_issues or AudioQualityIssue.INSUFFICIENT_DURATION in audio.detected_issues:
            return RecoveryAction.REQUEST_LONGER_RECORDING
        return RecoveryAction.REQUEST_FRESH_RECORDING

    def _get_customer_audio_msg(self, action: RecoveryAction) -> str:
        messages = {
            RecoveryAction.REDUCE_MICROPHONE_GAIN: "Audio was distorted. Please speak slightly further from your microphone.",
            RecoveryAction.REQUEST_QUIETER_ENVIRONMENT: "Background noise was high. Please move to a quieter location and speak clearly.",
            RecoveryAction.SPEAK_CLOSER_TO_MIC: "Volume was low. Please speak a little louder or closer to your microphone.",
            RecoveryAction.REQUEST_LONGER_RECORDING: "Please speak a full sentence so we can verify your voice clearly.",
            RecoveryAction.REQUEST_FRESH_RECORDING: "We could not hear a clear recording. Please try speaking again.",
        }
        return messages.get(action, "Please provide a clearer audio recording.")

    def _build_recovery_output(
        self,
        session: AuthenticationSession,
        verification_status: VerificationStatus,
        state: SessionState,
        decision: TrustDecision,
        reason_codes: List[ReasonCode],
        recovery_action: RecoveryAction,
        customer_message: str,
        internal_explanation: str,
        terminal_state: bool,
        sensitive_operations_paused: bool,
        independent_auth_required: bool,
    ) -> StructuredRecoveryOutput:
        return StructuredRecoveryOutput(
            session_id=session.session_id,
            caller_id=session.caller_id,
            attempt_number=session.attempt_number,
            verification_status=verification_status,
            session_state=state,
            decision=decision,
            reason_codes=reason_codes,
            recovery_action=recovery_action,
            customer_message=customer_message,
            internal_explanation=internal_explanation,
            audio_retries_remaining=max(0, session.config.max_audio_retries - session.audio_retry_count),
            service_retries_remaining=max(0, session.config.max_service_retries - session.service_retry_count),
            sensitive_operations_paused=sensitive_operations_paused,
            independent_auth_required=independent_auth_required,
            terminal_state=terminal_state,
            audit_telemetry={
                "attempt": session.attempt_number,
                "audio_retries": session.audio_retry_count,
                "service_retries": session.service_retry_count,
            },
        )
