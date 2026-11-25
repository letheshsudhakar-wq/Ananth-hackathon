"""
Adaptive Trust Engine Module for ANANTH (Strengthened for Phase 4).

Improvements:
- No direct subtraction or numerical comparison between Aletheia and Eidos scores.
- Semantic categorical verdicts: Authenticity (Liveness) vs Identity (Speaker recognition).
- Deepfake attack detection checks both validity and confidence reliability.
- Invalid evidence from one provider CANNOT suppress a credible attack from the other.
- All code branches have deterministic, explicit fail-closed outcomes.
- Configurable thresholds and non-calibrated probability indices.
"""

from typing import Optional, Union, Dict, Any, List
import math

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
    TrustEngineThresholds,
    TrustEngineOutput,
    MockVerificationEvidence,
)


class AdaptiveTrustEngine:
    """
    Core Deterministic Decision Engine for ANANTH.
    Evaluates evidence sources, resolves conflicts, and produces transparent authorization outcomes.
    """

    def __init__(
        self,
        thresholds: Optional[TrustEngineThresholds] = None,
        production_mode: bool = False,
    ):
        self.thresholds = thresholds or TrustEngineThresholds()
        self.production_mode = production_mode

    def evaluate(
        self,
        evidence: Union[MockVerificationEvidence, Dict[str, Any]],
        audio_quality: AudioQualityReport,
        aletheia_evidence: Optional[NormalizedAletheiaEvidence] = None,
        eidos_evidence: Optional[NormalizedEidosEvidence] = None,
        action_risk_level: Optional[ActionRiskLevel] = None,
    ) -> TrustEngineOutput:
        """
        Public evaluation interface. Supports both modern normalized evidence inputs
        and backwards-compatible MockVerificationEvidence payloads.
        """
        # Step 1: Normalize incoming evidence parameters
        aletheia, eidos, risk_level, is_mock_source = self._normalize_inputs(
            evidence, aletheia_evidence, eidos_evidence, action_risk_level
        )

        # Risk level validation - fail closed on unknown or invalid risk tier
        if not isinstance(risk_level, ActionRiskLevel):
            try:
                risk_level = ActionRiskLevel(str(risk_level).upper())
            except Exception:
                return TrustEngineOutput(
                    verification_status=VerificationStatus.INCONCLUSIVE,
                    decision=TrustDecision.DENY,
                    action_risk_level=ActionRiskLevel.HIGH,
                    evidence_completeness=0.0,
                    conflicting_evidence=False,
                    confidence_indicator=0.0,
                    reason_codes=[ReasonCode.INVALID_EVIDENCE_PAYLOAD],
                    explanation="Security violation: Unknown or invalid action risk level supplied. Operation failed closed.",
                    sensitive_operations_paused=True,
                    independent_auth_required=True,
                    audio_degradation_detected=False,
                    composite_trust_score=0.0,
                )

        # Step 2: Production Guardrail against Mock Evidence
        if self.production_mode and is_mock_source:
            return TrustEngineOutput(
                verification_status=VerificationStatus.INCONCLUSIVE,
                decision=TrustDecision.DENY,
                action_risk_level=risk_level,
                evidence_completeness=0.0,
                conflicting_evidence=False,
                confidence_indicator=0.0,
                reason_codes=[ReasonCode.MOCK_EVIDENCE_REJECTED_IN_PROD],
                explanation="Security violation: Mock evidence detected in production environment. Operation denied.",
                sensitive_operations_paused=True,
                independent_auth_required=True,
                audio_degradation_detected=False,
                composite_trust_score=0.0,
            )

        # Step 3: Compute Evidence Completeness
        completeness = self._calculate_evidence_completeness(audio_quality, aletheia, eidos)

        # Step 4: Rule Precedence 1 - Attack Escalation (Check FIRST!)
        # CRITICAL REFINEMENT: Even if one provider returned INVALID, MISSING, or corrupted data,
        # an invalid response CANNOT suppress a credible deepfake detected by Aletheia!
        attack_detected, attack_reason, attack_conf = self._check_credible_attack(aletheia)
        if attack_detected:
            # If Eidos reported a match, we flag conflicting evidence (classic spoofing pattern)
            conflicting = (
                eidos is not None and
                eidos.match_score is not None and
                eidos.match_score >= self.thresholds.min_voice_match_score
            )
            return TrustEngineOutput(
                verification_status=VerificationStatus.SUSPICIOUS,
                decision=TrustDecision.DENY,
                action_risk_level=risk_level,
                evidence_completeness=completeness,
                conflicting_evidence=conflicting,
                confidence_indicator=attack_conf,
                reason_codes=[ReasonCode.CREDIBLE_DEEPFAKE_DETECTED],
                explanation=f"Critical threat: {attack_reason}. Immediate security denial.",
                sensitive_operations_paused=True,
                independent_auth_required=True,
                audio_degradation_detected=not audio_quality.suitable_for_authentication,
                composite_trust_score=0.0,
            )

        # Step 5: Check for Invalid Evidence (NaN, Inf, Malformed Payload)
        if (aletheia and aletheia.status == EvidenceStatus.INVALID) or \
           (eidos and eidos.status == EvidenceStatus.INVALID):
            err_details = []
            if aletheia and aletheia.validation_errors:
                err_details.extend(aletheia.validation_errors)
            if eidos and eidos.validation_errors:
                err_details.extend(eidos.validation_errors)
            return TrustEngineOutput(
                verification_status=VerificationStatus.INCONCLUSIVE,
                decision=TrustDecision.DENY,
                action_risk_level=risk_level,
                evidence_completeness=completeness,
                conflicting_evidence=False,
                confidence_indicator=0.0,
                reason_codes=[ReasonCode.INVALID_EVIDENCE_PAYLOAD],
                explanation=f"Upstream verification evidence is invalid or non-finite: {'; '.join(err_details)}",
                sensitive_operations_paused=True,
                independent_auth_required=True,
                audio_degradation_detected=False,
                composite_trust_score=0.0,
            )

        # Step 6: Check for Missing / Unavailable APIs
        if self._is_missing_or_unavailable(aletheia) or self._is_missing_or_unavailable(eidos):
            missing_sources = []
            if self._is_missing_or_unavailable(aletheia):
                missing_sources.append("Aletheia (Authenticity)")
            if self._is_missing_or_unavailable(eidos):
                missing_sources.append("Eidos (Speaker Match)")

            return TrustEngineOutput(
                verification_status=VerificationStatus.INCONCLUSIVE,
                decision=TrustDecision.STEP_UP_CHALLENGE,
                action_risk_level=risk_level,
                evidence_completeness=completeness,
                conflicting_evidence=False,
                confidence_indicator=0.0,
                reason_codes=[ReasonCode.MISSING_OR_UNAVAILABLE_EVIDENCE],
                explanation=f"Required verification evidence is missing or unavailable ({', '.join(missing_sources)}). Secondary challenge required.",
                sensitive_operations_paused=True,
                independent_auth_required=True,
                audio_degradation_detected=False,
                composite_trust_score=0.0,
            )

        # Step 7: Rule Precedence 2 - Audio Quality Barrier
        # Strict Invariant: Poor audio NEVER weakens or bypasses authentication requirements
        if not audio_quality.suitable_for_authentication:
            return TrustEngineOutput(
                verification_status=VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED,
                decision=TrustDecision.RETRY_AUDIO,
                action_risk_level=risk_level,
                evidence_completeness=completeness,
                conflicting_evidence=False,
                confidence_indicator=0.0,
                reason_codes=[ReasonCode.POOR_AUDIO_QUALITY, ReasonCode.AUDIO_RETRY_REQUIRED],
                explanation="Audio signal quality is inadequate for biometric evaluation. "
                            "Authentication requirements cannot be weakened or bypassed.",
                sensitive_operations_paused=True,
                independent_auth_required=False,
                audio_degradation_detected=True,
                recovery_recommendation=audio_quality.recommended_action.value,
                composite_trust_score=0.0,
            )

        # Step 8: Rule Precedence 3 - Low Confidence Evaluation
        # Verified requires provider-specific confidence requirements
        aletheia_conf = aletheia.confidence if (aletheia and aletheia.confidence is not None) else 0.0
        eidos_conf = eidos.confidence if (eidos and eidos.confidence is not None) else 0.0
        low_confidence = (aletheia_conf < self.thresholds.min_confidence) or (eidos_conf < self.thresholds.min_confidence)

        if low_confidence:
            return TrustEngineOutput(
                verification_status=VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED,
                decision=TrustDecision.STEP_UP_CHALLENGE,
                action_risk_level=risk_level,
                evidence_completeness=completeness,
                conflicting_evidence=False,
                confidence_indicator=min(aletheia_conf, eidos_conf),
                reason_codes=[ReasonCode.LOW_CONFIDENCE_EVIDENCE],
                explanation="Upstream verification evidence returned insufficient confidence. Step-up secondary verification required.",
                sensitive_operations_paused=True,
                independent_auth_required=True,
                audio_degradation_detected=audio_quality.quality_status == AudioQualityStatus.MODERATE,
                composite_trust_score=0.3,
            )

        # Step 9: Rule Precedence 4 - Categorical Semantic Conflict Resolution
        # We do NOT subtract Aletheia and Eidos scores directly because they measure orthogonal dimensions!
        # Instead, evaluate categorical semantic verdicts:
        # Aletheia Verdict: AUTHENTIC_HUMAN vs SYNTHETIC vs UNCERTAIN
        # Eidos Verdict: MATCHING_IDENTITY vs IDENTITY_MISMATCH vs UNCERTAIN
        is_authentic_human = aletheia.liveness_score >= self.thresholds.min_liveness_score
        is_identity_match = eidos.match_score >= self.thresholds.min_voice_match_score
        is_identity_mismatch = eidos.match_score <= self.thresholds.max_impersonation_score

        # Case A: Human speech confirmed, but speaker identity does NOT match enrolled customer
        if is_authentic_human and is_identity_mismatch:
            return TrustEngineOutput(
                verification_status=VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED,
                decision=TrustDecision.STEP_UP_CHALLENGE,
                action_risk_level=risk_level,
                evidence_completeness=completeness,
                conflicting_evidence=True,
                confidence_indicator=min(aletheia_conf, eidos_conf),
                reason_codes=[ReasonCode.SPEAKER_IDENTITY_MISMATCH, ReasonCode.CONFLICTING_EVIDENCE],
                explanation="Voice is confirmed human, but speaker identity does not match enrolled profile. Secondary verification required.",
                sensitive_operations_paused=True,
                independent_auth_required=True,
                audio_degradation_detected=False,
                composite_trust_score=0.35,
            )

        # Case B: Disagreement in categorical status (e.g. one passed, one uncertain/sub-threshold)
        if is_authentic_human != is_identity_match:
            return TrustEngineOutput(
                verification_status=VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED,
                decision=TrustDecision.STEP_UP_CHALLENGE,
                action_risk_level=risk_level,
                evidence_completeness=completeness,
                conflicting_evidence=True,
                confidence_indicator=min(aletheia_conf, eidos_conf),
                reason_codes=[ReasonCode.CONFLICTING_EVIDENCE],
                explanation="Categorical divergence between voice authenticity and speaker identity match. Scores will not be averaged.",
                sensitive_operations_paused=True,
                independent_auth_required=True,
                audio_degradation_detected=False,
                composite_trust_score=0.4,
            )

        # Step 10: Rule Precedence 5 - Full Genuine Verification Check
        if is_authentic_human and is_identity_match:
            # Step 11: Security Safeguard - Financial Transactions & High Risk Operations
            # Voice verification alone NEVER authorizes financial operations!
            if risk_level in (ActionRiskLevel.FINANCIAL, ActionRiskLevel.HIGH) and self.thresholds.require_step_up_for_financial:
                return TrustEngineOutput(
                    verification_status=VerificationStatus.VERIFIED,
                    decision=TrustDecision.STEP_UP_CHALLENGE,
                    action_risk_level=risk_level,
                    evidence_completeness=completeness,
                    conflicting_evidence=False,
                    confidence_indicator=min(aletheia_conf, eidos_conf),
                    reason_codes=[
                        ReasonCode.VOICE_AND_IDENTITY_VERIFIED,
                        ReasonCode.FINANCIAL_TRANSACTION_STEP_UP_REQUIRED
                    ],
                    explanation="Voice and identity verified successfully. However, financial / high-risk operations "
                                "require mandatory step-up multi-factor authorization. Voice biometrics alone cannot authorize funds.",
                    sensitive_operations_paused=True,
                    independent_auth_required=True,
                    audio_degradation_detected=audio_quality.quality_status == AudioQualityStatus.MODERATE,
                    composite_trust_score=0.88,
                )

            # Standard Low/Medium risk allow
            return TrustEngineOutput(
                verification_status=VerificationStatus.VERIFIED,
                decision=TrustDecision.ALLOW,
                action_risk_level=risk_level,
                evidence_completeness=completeness,
                conflicting_evidence=False,
                confidence_indicator=min(aletheia_conf, eidos_conf),
                reason_codes=[ReasonCode.VOICE_AND_IDENTITY_VERIFIED],
                explanation="Voice authenticity and speaker identity verified with adequate audio quality and confidence.",
                sensitive_operations_paused=False,
                independent_auth_required=False,
                audio_degradation_detected=audio_quality.quality_status == AudioQualityStatus.MODERATE,
                composite_trust_score=0.92,
            )

        # Fail-closed fallback: Neither passed or scores sub-threshold
        return TrustEngineOutput(
            verification_status=VerificationStatus.ADDITIONAL_VERIFICATION_REQUIRED,
            decision=TrustDecision.STEP_UP_CHALLENGE,
            action_risk_level=risk_level,
            evidence_completeness=completeness,
            conflicting_evidence=False,
            confidence_indicator=min(aletheia_conf, eidos_conf),
            reason_codes=[ReasonCode.SPEAKER_IDENTITY_MISMATCH],
            explanation="Biometric scores did not meet required authentication threshold. Secondary challenge required.",
            sensitive_operations_paused=True,
            independent_auth_required=True,
            audio_degradation_detected=False,
            composite_trust_score=0.45,
        )

    # --------------------------------------------------------------------------
    # Helper Methods
    # --------------------------------------------------------------------------

    def _normalize_inputs(
        self,
        evidence: Union[MockVerificationEvidence, Dict[str, Any]],
        aletheia_evidence: Optional[NormalizedAletheiaEvidence],
        eidos_evidence: Optional[NormalizedEidosEvidence],
        action_risk_level: Optional[ActionRiskLevel],
    ) -> tuple[NormalizedAletheiaEvidence, NormalizedEidosEvidence, ActionRiskLevel, bool]:
        """Maps diverse inputs into uniform Normalized evidence dataclasses."""
        is_mock = False

        if isinstance(evidence, MockVerificationEvidence):
            is_mock = evidence.is_mock
            risk = action_risk_level or evidence.requested_action_risk
            aletheia = aletheia_evidence or NormalizedAletheiaEvidence(
                liveness_score=evidence.aletheia_liveness_score,
                confidence=evidence.aletheia_confidence,
                is_mock=evidence.is_mock,
            )
            eidos = eidos_evidence or NormalizedEidosEvidence(
                match_score=evidence.eidos_voice_match_score,
                confidence=evidence.eidos_confidence,
                is_mock=evidence.is_mock,
            )
            return aletheia, eidos, risk, is_mock

        # When evidence is passed as normalized objects or dict
        risk = action_risk_level or ActionRiskLevel.MEDIUM
        aletheia = aletheia_evidence or NormalizedAletheiaEvidence(status=EvidenceStatus.MISSING)
        eidos = eidos_evidence or NormalizedEidosEvidence(status=EvidenceStatus.MISSING)
        is_mock = getattr(aletheia, "is_mock", False) or getattr(eidos, "is_mock", False)
        return aletheia, eidos, risk, is_mock

    def _is_missing_or_unavailable(self, ev: Optional[Union[NormalizedAletheiaEvidence, NormalizedEidosEvidence]]) -> bool:
        if ev is None:
            return True
        return ev.status in (EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE)

    def _calculate_evidence_completeness(
        self,
        audio: AudioQualityReport,
        aletheia: Optional[NormalizedAletheiaEvidence],
        eidos: Optional[NormalizedEidosEvidence]
    ) -> float:
        points = 0.0
        if audio and audio.valid:
            points += 1.0
        if aletheia and aletheia.status not in (EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE, EvidenceStatus.INVALID):
            points += 1.0
        if eidos and eidos.status not in (EvidenceStatus.MISSING, EvidenceStatus.UNAVAILABLE, EvidenceStatus.INVALID):
            points += 1.0
        return points / 3.0

    def _check_credible_attack(
        self,
        aletheia: Optional[NormalizedAletheiaEvidence],
    ) -> tuple[bool, str, float]:
        """
        Validates both the validity and reliability of Aletheia anti-spoof evidence.
        """
        if aletheia and aletheia.liveness_score is not None:
            # Check validity first: non-finite or negative values do not trigger attack
            if math.isnan(aletheia.liveness_score) or math.isinf(aletheia.liveness_score):
                return False, "", 0.0

            if 0.0 <= aletheia.liveness_score <= self.thresholds.max_spoof_score:
                confidence = aletheia.confidence or 0.0
                # Must be reliable evidence (confidence >= 0.60)
                if confidence >= 0.60:
                    return (
                        True,
                        f"Aletheia flagged synthetic speech (liveness: {aletheia.liveness_score:.2f}, conf: {confidence:.2f})",
                        confidence,
                    )

        return False, "", 0.0
