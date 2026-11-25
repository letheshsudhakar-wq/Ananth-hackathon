"""
src/agentic/cross_language_identity.py — Agent 5: Cross-Language Identity Agent.

Objective:
Handle users who enroll in one language and authenticate in another:
- Enrollment language retrieval & current language comparison.
- Language switching / mismatch detection.
- Cross-language identity verification check with Eidos speaker evidence.
- Strict security invariants:
  - Inconclusive or mismatched language evidence must NOT fail open.
  - Never translate or synthesize customer audio for biometric verification.
  - Never automatically enroll a new voice sample without independent multi-factor verification and explicit user consent.
"""

from __future__ import annotations

import time
import math
from typing import Dict, Any, Optional, List, Union

from src.agentic.schemas import StandardAgentResponse, AgentStatus


class CrossLanguageIdentityAgent:
    """Agent 5: Evaluates language switching between enrollment and current authentication session."""

    AGENT_NAME = "cross_language_identity_agent"

    def __init__(self, cross_language_penalty_threshold: float = 0.65):
        self.cross_language_penalty_threshold = cross_language_penalty_threshold

    def evaluate(
        self,
        session_id: str,
        enrolled_language: Optional[str],
        current_language: str,
        eidos_match_score: Optional[float] = None,
        eidos_confidence: Optional[float] = None,
    ) -> StandardAgentResponse:
        t0 = time.perf_counter()
        limitations: List[str] = [
            "Cross-language acoustic variance may moderately suppress raw speaker similarity scores.",
            "Never perform voice synthesis or translation for biometric verification.",
            "Automatic voice re-enrollment across languages is prohibited without multi-factor consent.",
        ]

        norm_enrolled = (enrolled_language or "unknown").lower().strip()
        norm_current = (current_language or "unknown").lower().strip()
        has_language_switch = (
            norm_enrolled != "unknown"
            and norm_current != "unknown"
            and norm_enrolled != norm_current
        )

        score = eidos_match_score
        conf = eidos_confidence if eidos_confidence is not None else 0.80

        # Identity evidence evaluation
        if score is None:
            status = AgentStatus.INCONCLUSIVE
            recommended_action = "REQUEST_ENROLLED_LANGUAGE_SAMPLE"
            findings_summary = (
                f"Language switch detected ({norm_enrolled} -> {norm_current}) with missing speaker evidence."
            )
            evidence_reliability = 0.0
        elif has_language_switch:
            # Language switch occurred
            if score >= 0.75:
                # Strong speaker match even across language switch
                status = AgentStatus.PASS
                recommended_action = "PROCEED"
                findings_summary = (
                    f"Language switch observed ({norm_enrolled} -> {norm_current}), "
                    f"but speaker acoustic identity matches robustly (score: {score:.2f})."
                )
                evidence_reliability = conf
            elif score >= self.cross_language_penalty_threshold:
                # Borderline match due to language shift
                status = AgentStatus.WARNING
                recommended_action = "REQUEST_ENROLLED_LANGUAGE_SAMPLE"
                findings_summary = (
                    f"Language switch detected ({norm_enrolled} -> {norm_current}) with borderline match ({score:.2f}). "
                    f"Prompt user to authenticate in enrolled language ({norm_enrolled}) to eliminate phonetic mismatch."
                )
                evidence_reliability = conf * 0.85
            else:
                # Identity mismatch
                status = AgentStatus.WARNING
                recommended_action = "STEP_UP_CHALLENGE"
                findings_summary = (
                    f"Speaker mismatch observed during cross-language session ({norm_enrolled} -> {norm_current}, score: {score:.2f})."
                )
                evidence_reliability = conf
        else:
            # Same language or enrollment language not established
            if score >= 0.70:
                status = AgentStatus.PASS
                recommended_action = "PROCEED"
                findings_summary = f"Same-language verification confirmed (language: {norm_current}, score: {score:.2f})."
                evidence_reliability = conf
            else:
                status = AgentStatus.WARNING
                recommended_action = "STEP_UP_CHALLENGE"
                findings_summary = f"Low speaker similarity ({score:.2f}) under {norm_current} speech."
                evidence_reliability = conf

        findings: Dict[str, Any] = {
            "enrolled_language": norm_enrolled,
            "current_language": norm_current,
            "language_switching_detected": has_language_switch,
            "eidos_match_score": score,
            "evidence_reliability": round(evidence_reliability, 3),
            "summary": findings_summary,
        }

        measurements: Dict[str, Optional[float]] = {
            "eidos_match_score": score,
            "evidence_reliability": evidence_reliability,
            "language_switched": 1.0 if has_language_switch else 0.0,
        }

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return StandardAgentResponse(
            agent_name=self.AGENT_NAME,
            session_id=session_id,
            status=status,
            findings=findings,
            measurements=measurements,
            confidence=evidence_reliability,
            limitations=limitations,
            recommended_action=recommended_action,
            processing_time_ms=elapsed_ms,
            error=None,
        )
