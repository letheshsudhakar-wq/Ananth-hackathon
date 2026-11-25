"""
Explainable Decision Engine for ANANTH (Member 3).

Generates deterministic, transparent explanations from actual decision evidence without using LLMs.
Separates customer-facing instructions from internal security audit explanations.

Strict Invariants:
- Never reveal internal thresholds or attack-detection weaknesses in customer-facing messages.
- Never fabricate evidence or confidence values.
- Provide comprehensive audit telemetry for compliance and fraud operations.
"""

from typing import List, Dict, Any, Optional

from src.schemas import (
    AudioQualityReport,
    AudioQualityStatus,
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    TrustEngineOutput,
    ExplanationDetail,
    ReasonCode,
    VerificationStatus,
    TrustDecision,
    ActionRiskLevel,
    StructuredRecoveryOutput,
)


class DecisionExplainer:
    """
    Deterministic Decision Explainer.
    Produces paired (Customer-Facing vs Internal Security Audit) explanations.
    """

    @staticmethod
    def explain(
        trust_output: TrustEngineOutput,
        audio_report: AudioQualityReport,
        aletheia: Optional[NormalizedAletheiaEvidence] = None,
        eidos: Optional[NormalizedEidosEvidence] = None,
        recovery_output: Optional[StructuredRecoveryOutput] = None,
    ) -> ExplanationDetail:
        """
        Builds a comprehensive explanation package.
        """
        # 1. Short decision summary
        short_summary = f"{trust_output.verification_status.value}: Action {trust_output.decision.value}"

        # 2. Audio quality issues
        audio_issues = [f"{issue.value}: {note}" for issue, note in zip(audio_report.detected_issues, audio_report.quality_notes)] if audio_report.detected_issues else audio_report.quality_notes

        # 3. Evidence summary (audited evidence without raw biometrics)
        evidence_summary = {
            "audio_quality_status": audio_report.quality_status.value,
            "snr_db": audio_report.estimated_snr_db,
            "speech_duration_s": audio_report.estimated_speech_duration_seconds,
            "clipping_pct": audio_report.clipping_percentage,
            "aletheia_status": aletheia.status.value if aletheia else "NOT_PROVIDED",
            "aletheia_liveness_score": aletheia.liveness_score if aletheia else None,
            "aletheia_confidence": aletheia.confidence if aletheia else None,
            "eidos_status": eidos.status.value if eidos else "NOT_PROVIDED",
            "eidos_match_score": eidos.match_score if eidos else None,
            "eidos_confidence": eidos.confidence if eidos else None,
            "completeness": trust_output.evidence_completeness,
        }

        # 4. Detected conflicts
        detected_conflicts = []
        if trust_output.conflicting_evidence:
            if ReasonCode.CREDIBLE_DEEPFAKE_DETECTED in trust_output.reason_codes and (eidos and eidos.match_score and eidos.match_score > 0.7):
                detected_conflicts.append("Synthetic audio artifact detected despite high enrolled voice timbre match (Possible AI clone).")
            elif ReasonCode.SPEAKER_IDENTITY_MISMATCH in trust_output.reason_codes:
                detected_conflicts.append("Natural human speech verified, but speaker vocal tract features diverge from customer profile.")
            else:
                detected_conflicts.append("Categorical divergence between voice authenticity and speaker recognition models.")

        # 5. Security restrictions
        security_restrictions = []
        if trust_output.sensitive_operations_paused:
            security_restrictions.append("Sensitive account actions remain paused.")
        if trust_output.independent_auth_required:
            security_restrictions.append("Secondary independent out-of-band authentication mandatory.")
        if trust_output.action_risk_level in (ActionRiskLevel.FINANCIAL, ActionRiskLevel.HIGH):
            security_restrictions.append("Financial transaction policy strictly forbids voice-only authorization.")

        # 6. Customer-facing message (Helpful, respectful, zero threshold leaks)
        customer_msg = DecisionExplainer._generate_customer_message(trust_output, audio_report, recovery_output)

        # 7. Internal security audit explanation (Transparent, rigorous, audited)
        internal_exp = DecisionExplainer._generate_internal_audit_explanation(
            trust_output, audio_report, aletheia, eidos, recovery_output
        )

        recovery_action_str = recovery_output.recovery_action.value if recovery_output else "PROCEED"

        return ExplanationDetail(
            short_summary=short_summary,
            customer_message=customer_msg,
            internal_explanation=internal_exp,
            audio_issues=audio_issues,
            evidence_summary=evidence_summary,
            detected_conflicts=detected_conflicts,
            reason_codes=[rc.value for rc in trust_output.reason_codes],
            recommended_recovery_action=recovery_action_str,
            security_restrictions=security_restrictions,
        )

    @staticmethod
    def _generate_customer_message(
        output: TrustEngineOutput,
        audio: AudioQualityReport,
        recovery: Optional[StructuredRecoveryOutput],
    ) -> str:
        """Friendly customer instruction that NEVER leaks internal security thresholds."""
        if recovery and recovery.customer_message:
            return recovery.customer_message

        if output.decision == TrustDecision.ALLOW:
            return "Voice authentication successful. Your request has been approved."

        if ReasonCode.CREDIBLE_DEEPFAKE_DETECTED in output.reason_codes:
            return "Voice authentication could not be completed for security reasons. Please contact customer support."

        if ReasonCode.FINANCIAL_TRANSACTION_STEP_UP_REQUIRED in output.reason_codes:
            return "Your voice identity was recognized. To complete this financial transaction, please confirm using your registered backup method."

        if output.decision == TrustDecision.RETRY_AUDIO:
            return "We could not hear your voice clearly. Please speak clearly into your microphone in a quiet area."

        if output.decision == TrustDecision.STEP_UP_CHALLENGE:
            return "We need to confirm your identity using an additional security verification method."

        return "Unable to complete voice verification at this time. Please try an alternate method."

    @staticmethod
    def _generate_internal_audit_explanation(
        output: TrustEngineOutput,
        audio: AudioQualityReport,
        aletheia: Optional[NormalizedAletheiaEvidence],
        eidos: Optional[NormalizedEidosEvidence],
        recovery: Optional[StructuredRecoveryOutput],
    ) -> str:
        """Detailed technical audit report with exact reason codes and evidence telemetry."""
        reasons = [rc.value for rc in output.reason_codes]
        base_exp = output.explanation

        details = [
            f"Verdict: {output.verification_status.value}",
            f"Decision: {output.decision.value}",
            f"Risk: {output.action_risk_level.value}",
            f"ReasonCodes: [{', '.join(reasons)}]",
            f"Completeness: {output.evidence_completeness * 100:.0f}%",
            f"ConfIndicator: {output.confidence_indicator:.2f}",
        ]

        if aletheia:
            details.append(f"Aletheia(liveness={aletheia.liveness_score}, conf={aletheia.confidence}, status={aletheia.status.value})")
        if eidos:
            details.append(f"Eidos(match={eidos.match_score}, conf={eidos.confidence}, status={eidos.status.value})")

        if recovery:
            details.append(f"SessionState: {recovery.session_state.value}")
            details.append(f"RecoveryAction: {recovery.recovery_action.value}")

        return f"{base_exp} | Audit Telemetry: {' | '.join(details)}"
