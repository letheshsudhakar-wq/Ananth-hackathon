"""
Data Contracts and Schema Definitions for Member 3.

Provides lightweight, dependency-free dataclass contracts for:
1. Audio Quality Assessment (inputs, outputs, classifications, issues)
2. Normalized Upstream Verification Evidence (Aletheia & Eidos)
3. Adaptive Trust Engine Outputs & Safeguards
4. Phase 4: Adaptive Recovery, Multi-turn Session State Machine & Explainability
"""

from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Dict, List, Optional, Any, Union


# ==============================================================================
# ENUMS
# ==============================================================================

class AudioQualityStatus(str, Enum):
    GOOD = "GOOD"
    MODERATE = "MODERATE"
    POOR = "POOR"
    INVALID = "INVALID"


class AudioQualityIssue(str, Enum):
    FILE_MISSING = "FILE_MISSING"
    FILE_EMPTY = "FILE_EMPTY"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    INVALID_SAMPLE_RATE = "INVALID_SAMPLE_RATE"
    NON_FINITE_SAMPLES = "NON_FINITE_SAMPLES"
    EXCESSIVE_DURATION = "EXCESSIVE_DURATION"
    INSUFFICIENT_DURATION = "INSUFFICIENT_DURATION"
    LOW_RECORDING_VOLUME = "LOW_RECORDING_VOLUME"
    EXCESSIVE_BACKGROUND_NOISE = "EXCESSIVE_BACKGROUND_NOISE"
    AUDIO_CLIPPING = "AUDIO_CLIPPING"
    EXCESSIVE_SILENCE = "EXCESSIVE_SILENCE"
    INSUFFICIENT_SPEECH = "INSUFFICIENT_SPEECH"


class RecommendedAction(str, Enum):
    """Acoustic recommendations from audio quality assessor."""
    PROCEED = "PROCEED"
    REQUEST_LONGER_RECORDING = "REQUEST_LONGER_RECORDING"
    REQUEST_QUIETER_ENVIRONMENT = "REQUEST_QUIETER_ENVIRONMENT"
    SPEAK_CLOSER_TO_MIC = "SPEAK_CLOSER_TO_MIC"
    REDUCE_MICROPHONE_GAIN = "REDUCE_MICROPHONE_GAIN"
    REQUEST_FRESH_RECORDING = "REQUEST_FRESH_RECORDING"


class EvidenceStatus(str, Enum):
    """Status of upstream normalized evidence."""
    VALID = "VALID"
    MISSING = "MISSING"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class VerificationStatus(str, Enum):
    """Verification factual outcome."""
    VERIFIED = "VERIFIED"
    SUSPICIOUS = "SUSPICIOUS"
    INCONCLUSIVE = "INCONCLUSIVE"
    ADDITIONAL_VERIFICATION_REQUIRED = "ADDITIONAL_VERIFICATION_REQUIRED"


class TrustDecision(str, Enum):
    """Authorization action."""
    ALLOW = "ALLOW"
    STEP_UP_CHALLENGE = "STEP_UP_CHALLENGE"
    RETRY_AUDIO = "RETRY_AUDIO"
    DENY = "DENY"


class ActionRiskLevel(str, Enum):
    """Risk tier for the user action being authenticated."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    FINANCIAL = "FINANCIAL"


class ReasonCode(str, Enum):
    """Machine-readable decision reason codes."""
    VOICE_AND_IDENTITY_VERIFIED = "VOICE_AND_IDENTITY_VERIFIED"
    CREDIBLE_DEEPFAKE_DETECTED = "CREDIBLE_DEEPFAKE_DETECTED"
    SPEAKER_IDENTITY_MISMATCH = "SPEAKER_IDENTITY_MISMATCH"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    POOR_AUDIO_QUALITY = "POOR_AUDIO_QUALITY"
    AUDIO_RETRY_REQUIRED = "AUDIO_RETRY_REQUIRED"
    LOW_CONFIDENCE_EVIDENCE = "LOW_CONFIDENCE_EVIDENCE"
    MISSING_OR_UNAVAILABLE_EVIDENCE = "MISSING_OR_UNAVAILABLE_EVIDENCE"
    INVALID_EVIDENCE_PAYLOAD = "INVALID_EVIDENCE_PAYLOAD"
    MOCK_EVIDENCE_REJECTED_IN_PROD = "MOCK_EVIDENCE_REJECTED_IN_PROD"
    HIGH_RISK_INDEPENDENT_AUTH_REQUIRED = "HIGH_RISK_INDEPENDENT_AUTH_REQUIRED"
    FINANCIAL_TRANSACTION_STEP_UP_REQUIRED = "FINANCIAL_TRANSACTION_STEP_UP_REQUIRED"
    AUDIO_RETRY_LIMIT_EXCEEDED = "AUDIO_RETRY_LIMIT_EXCEEDED"
    SERVICE_RETRY_LIMIT_EXCEEDED = "SERVICE_RETRY_LIMIT_EXCEEDED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_LOCKED_SUSPICIOUS = "SESSION_LOCKED_SUSPICIOUS"
    STALE_EVIDENCE_REJECTED = "STALE_EVIDENCE_REJECTED"
    CROSS_SESSION_EVIDENCE_REJECTED = "CROSS_SESSION_EVIDENCE_REJECTED"


class RecoveryAction(str, Enum):
    """
    Intelligent actionable recovery recommendation from Adaptive Recovery Engine.
    Prioritized by risk: Credible attack / locks take top priority.
    """
    REQUEST_LONGER_RECORDING = "REQUEST_LONGER_RECORDING"
    REQUEST_QUIETER_ENVIRONMENT = "REQUEST_QUIETER_ENVIRONMENT"
    SPEAK_CLOSER_TO_MIC = "SPEAK_CLOSER_TO_MIC"
    REDUCE_MICROPHONE_GAIN = "REDUCE_MICROPHONE_GAIN"
    REQUEST_FRESH_RECORDING = "REQUEST_FRESH_RECORDING"
    RETRY_VERIFICATION_SERVICE = "RETRY_VERIFICATION_SERVICE"
    REQUIRE_INDEPENDENT_AUTHENTICATION = "REQUIRE_INDEPENDENT_AUTHENTICATION"
    ESCALATE_FOR_MANUAL_REVIEW = "ESCALATE_FOR_MANUAL_REVIEW"
    BLOCK_SUSPICIOUS_SESSION = "BLOCK_SUSPICIOUS_SESSION"
    VERIFICATION_COMPLETE = "VERIFICATION_COMPLETE"


class SessionState(str, Enum):
    """
    States for the Multi-turn Authentication Session State Machine.
    """
    INITIAL = "INITIAL"
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    RETRY_AUDIO = "RETRY_AUDIO"
    RETRY_SERVICE = "RETRY_SERVICE"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    VOICE_VERIFIED = "VOICE_VERIFIED"
    ESCALATED = "ESCALATED"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"


# ==============================================================================
# CONFIGURATION & THRESHOLDS
# ==============================================================================

@dataclass
class AudioQualityThresholds:
    """Configurable thresholds for acoustic quality assessment."""
    min_duration_seconds: float = 1.0
    max_duration_seconds: float = 30.0
    min_sample_rate: int = 8000
    max_sample_rate: int = 48000
    max_file_size_bytes: int = 25 * 1024 * 1024
    min_speech_duration_seconds: float = 1.2
    max_silence_percentage: float = 75.0
    max_clipping_percentage: float = 1.0
    min_rms_dbfs: float = -42.0
    min_snr_db_good: float = 15.0
    min_snr_db_moderate: float = 8.0
    max_noise_level_dbfs: float = -28.0


@dataclass
class ProviderApiDurationLimits:
    aletheia_min_duration_seconds: float = 1.0
    aletheia_max_duration_seconds: float = 30.0
    eidos_min_duration_seconds: float = 1.5
    eidos_max_duration_seconds: float = 30.0


@dataclass
class TrustEngineThresholds:
    """
    Centralized configurable decision thresholds for Adaptive Trust Engine.
    Not calibrated probabilities; these are deterministic security criteria.
    """
    min_confidence: float = 0.65                # Below this, marked LOW_CONFIDENCE
    min_liveness_score: float = 0.70            # Aletheia authenticity pass threshold
    max_spoof_score: float = 0.35               # Below this, credible deepfake indicator
    min_voice_match_score: float = 0.75         # Eidos speaker match pass threshold
    max_impersonation_score: float = 0.40       # Below this, identity mismatch
    require_step_up_for_financial: bool = True  # Strict safeguard: voice alone cannot authorize funds


@dataclass
class RecoveryConfig:
    """
    Configurable limits for session state machine.
    Provisional hackathon defaults.
    """
    max_audio_retries: int = 3
    max_service_retries: int = 2
    session_timeout_seconds: float = 300.0      # 5 minutes


# ==============================================================================
# AUDIO & EVIDENCE SCHEMAS
# ==============================================================================

@dataclass
class AudioAssessmentInput:
    sample_rate: int
    audio_path: Optional[str] = None
    channels: int = 1
    duration_seconds: float = 0.0


@dataclass
class AudioQualityReport:
    valid: bool
    quality_status: AudioQualityStatus
    suitable_for_authentication: bool
    duration_seconds: float
    estimated_speech_duration_seconds: Optional[float]
    sample_rate: Optional[int]
    channel_count: Optional[int]
    estimated_noise_level_dbfs: Optional[float]
    estimated_snr_db: Optional[float]
    silence_percentage: Optional[float]
    clipping_percentage: Optional[float]
    rms_dbfs: Optional[float]
    peak_amplitude: Optional[float]
    detected_issues: List[AudioQualityIssue] = field(default_factory=list)
    recommended_action: RecommendedAction = RecommendedAction.PROCEED
    quality_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "quality_status": self.quality_status.value,
            "suitable_for_authentication": self.suitable_for_authentication,
            "duration_seconds": round(self.duration_seconds, 3),
            "estimated_speech_duration_seconds": round(self.estimated_speech_duration_seconds, 3) if self.estimated_speech_duration_seconds is not None else None,
            "sample_rate": self.sample_rate,
            "channel_count": self.channel_count,
            "estimated_noise_level_dbfs": round(self.estimated_noise_level_dbfs, 2) if self.estimated_noise_level_dbfs is not None else None,
            "estimated_snr_db": round(self.estimated_snr_db, 2) if self.estimated_snr_db is not None else None,
            "silence_percentage": round(self.silence_percentage, 2) if self.silence_percentage is not None else None,
            "clipping_percentage": round(self.clipping_percentage, 3) if self.clipping_percentage is not None else None,
            "rms_dbfs": round(self.rms_dbfs, 2) if self.rms_dbfs is not None else None,
            "peak_amplitude": round(self.peak_amplitude, 4) if self.peak_amplitude is not None else None,
            "detected_issues": [issue.value for issue in self.detected_issues],
            "recommended_action": self.recommended_action.value,
            "quality_notes": self.quality_notes,
        }


def _is_valid_float_unit_interval(val: Any) -> bool:
    if val is None or not isinstance(val, (int, float)):
        return False
    if math.isnan(val) or math.isinf(val):
        return False
    return 0.0 <= float(val) <= 1.0


@dataclass
class NormalizedAletheiaEvidence:
    """
    Normalized authenticity & anti-spoofing evidence from Aletheia API.
    Scores: 0.0 = synthetic/spoof, 1.0 = authentic human voice.
    Bound to session_id and attempt_number for tamper resistance.
    """
    liveness_score: Optional[float] = None
    confidence: Optional[float] = None
    status: EvidenceStatus = EvidenceStatus.VALID
    is_mock: bool = False
    session_id: Optional[str] = None
    attempt_number: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    provider_raw_status: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        if self.status in (EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE):
            return

        errors = []
        if self.liveness_score is None:
            errors.append("liveness_score is missing")
        elif not _is_valid_float_unit_interval(self.liveness_score):
            errors.append(f"liveness_score out of range or non-finite: {self.liveness_score}")

        if self.confidence is None:
            errors.append("confidence is missing")
        elif not _is_valid_float_unit_interval(self.confidence):
            errors.append(f"confidence out of range or non-finite: {self.confidence}")

        if errors:
            self.status = EvidenceStatus.INVALID
            self.validation_errors.extend(errors)
        elif self.confidence is not None and self.confidence < 0.65:
            self.status = EvidenceStatus.LOW_CONFIDENCE


@dataclass
class NormalizedEidosEvidence:
    """
    Normalized speaker identity evidence from Eidos API.
    Scores: 0.0 = non-matching voice timbre, 1.0 = strong enrolled match.
    Bound to session_id and attempt_number for tamper resistance.
    """
    match_score: Optional[float] = None
    confidence: Optional[float] = None
    status: EvidenceStatus = EvidenceStatus.VALID
    is_mock: bool = False
    enrolled_profile_found: bool = True
    session_id: Optional[str] = None
    attempt_number: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    provider_raw_status: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        if self.status in (EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE):
            return

        errors = []
        if self.match_score is None:
            errors.append("match_score is missing")
        elif not _is_valid_float_unit_interval(self.match_score):
            errors.append(f"match_score out of range or non-finite: {self.match_score}")

        if self.confidence is None:
            errors.append("confidence is missing")
        elif not _is_valid_float_unit_interval(self.confidence):
            errors.append(f"confidence out of range or non-finite: {self.confidence}")

        if not self.enrolled_profile_found:
            errors.append("enrolled voice profile not found for caller")

        if errors:
            self.status = EvidenceStatus.INVALID
            self.validation_errors.extend(errors)
        elif self.confidence is not None and self.confidence < 0.65:
            self.status = EvidenceStatus.LOW_CONFIDENCE


# ==============================================================================
# TRUST ENGINE OUTPUT SCHEMA
# ==============================================================================

@dataclass
class TrustEngineOutput:
    """
    Structured outcome returned by AdaptiveTrustEngine.evaluate().
    """
    verification_status: VerificationStatus
    decision: TrustDecision
    action_risk_level: ActionRiskLevel
    evidence_completeness: float
    conflicting_evidence: bool
    confidence_indicator: float
    reason_codes: List[ReasonCode]
    explanation: str
    sensitive_operations_paused: bool
    independent_auth_required: bool
    audio_degradation_detected: bool
    recovery_recommendation: Optional[str] = None
    composite_trust_score: float = 0.0
    audit_telemetry: Dict[str, Any] = field(default_factory=dict)

    # Backwards compatibility properties:
    confidence_level: Optional[float] = None
    risk_tier: Optional[ActionRiskLevel] = None

    def __post_init__(self):
        if self.confidence_level is None:
            self.confidence_level = self.confidence_indicator
        if self.risk_tier is None:
            self.risk_tier = self.action_risk_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verification_status": self.verification_status.value,
            "decision": self.decision.value,
            "action_risk_level": self.action_risk_level.value,
            "evidence_completeness": round(self.evidence_completeness, 2),
            "conflicting_evidence": self.conflicting_evidence,
            "confidence_indicator": round(self.confidence_indicator, 2),
            "reason_codes": [rc.value for rc in self.reason_codes],
            "explanation": self.explanation,
            "sensitive_operations_paused": self.sensitive_operations_paused,
            "independent_auth_required": self.independent_auth_required,
            "audio_degradation_detected": self.audio_degradation_detected,
            "recovery_recommendation": self.recovery_recommendation,
            "composite_trust_score": round(self.composite_trust_score, 3),
            "audit_telemetry": self.audit_telemetry,
        }


# ==============================================================================
# PHASE 4: SESSION & EXPLAINABILITY SCHEMAS
# ==============================================================================

@dataclass
class ExplanationDetail:
    """
    Detailed, explainable reasoning package separating customer instructions
    from internal security telemetry.
    """
    short_summary: str
    customer_message: str                   # Clean, friendly message with NO sensitive thresholds
    internal_explanation: str              # Technical, audited rationale for logs/ops
    audio_issues: List[str]
    evidence_summary: Dict[str, Any]
    detected_conflicts: List[str]
    reason_codes: List[str]
    recommended_recovery_action: str
    security_restrictions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "short_summary": self.short_summary,
            "customer_message": self.customer_message,
            "internal_explanation": self.internal_explanation,
            "audio_issues": self.audio_issues,
            "evidence_summary": self.evidence_summary,
            "detected_conflicts": self.detected_conflicts,
            "reason_codes": self.reason_codes,
            "recommended_recovery_action": self.recommended_recovery_action,
            "security_restrictions": self.security_restrictions,
        }


@dataclass
class StructuredRecoveryOutput:
    """
    Comprehensive structured recovery output consumable by Member 2 (API)
    and Member 1 (Frontend JSON).
    """
    session_id: str
    caller_id: str
    attempt_number: int
    verification_status: VerificationStatus
    session_state: SessionState
    decision: TrustDecision
    reason_codes: List[ReasonCode]
    recovery_action: RecoveryAction
    customer_message: str
    internal_explanation: str
    audio_retries_remaining: int
    service_retries_remaining: int
    sensitive_operations_paused: bool
    independent_auth_required: bool
    terminal_state: bool
    audit_telemetry: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "caller_id": self.caller_id,
            "attempt_number": self.attempt_number,
            "verification_status": self.verification_status.value,
            "session_state": self.session_state.value,
            "decision": self.decision.value,
            "reason_codes": [rc.value for rc in self.reason_codes],
            "recovery_action": self.recovery_action.value,
            "customer_message": self.customer_message,
            "internal_explanation": self.internal_explanation,
            "audio_retries_remaining": self.audio_retries_remaining,
            "service_retries_remaining": self.service_retries_remaining,
            "sensitive_operations_paused": self.sensitive_operations_paused,
            "independent_auth_required": self.independent_auth_required,
            "terminal_state": self.terminal_state,
            "audit_telemetry": self.audit_telemetry,
        }


@dataclass
class MockVerificationEvidence:
    caller_id: str
    aletheia_liveness_score: float
    aletheia_confidence: float
    eidos_voice_match_score: float
    eidos_confidence: float
    requested_action_risk: ActionRiskLevel = ActionRiskLevel.MEDIUM
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_mock: bool = True
