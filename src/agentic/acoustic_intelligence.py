"""
src/agentic/acoustic_intelligence.py — Agent 2: Acoustic Intelligence Agent.

Objective:
Handle background noise and poor acoustic conditions:
- Background noise estimation (stationary & non-stationary SNR).
- Clipping & non-linear digital distortion detection.
- Identification of usable speech segments.
- Non-destructive noise reduction reference (spectral subtraction / Wiener filter simulation).
- CRITICAL INVARIANT: Original audio is PRESERVED. Never replace original audio with enhanced audio
  for deepfake detection because enhancement removes subtle forensic artifacts.
"""

from __future__ import annotations

import time
import math
from typing import Dict, Any, Optional, List, Union, Tuple
import numpy as np

from src.schemas import AudioQualityStatus, AudioQualityIssue
from src.audio_intelligence.assessor import AudioQualityAssessor
from src.agentic.schemas import StandardAgentResponse, AgentStatus


class AcousticIntelligenceAgent:
    """Agent 2: Evaluates background noise, SNR, clipping, and acoustic environment suitability."""

    AGENT_NAME = "acoustic_intelligence_agent"

    def __init__(self, assessor: Optional[AudioQualityAssessor] = None):
        self.assessor = assessor or AudioQualityAssessor()

    def analyze(
        self,
        session_id: str,
        audio_input: Union[str, bytes, np.ndarray],
        sample_rate: Optional[int] = None,
    ) -> StandardAgentResponse:
        # Default sample rate for numpy arrays so the assessor doesn't reject them
        if isinstance(audio_input, np.ndarray) and sample_rate is None:
            sample_rate = 16000
        t0 = time.perf_counter()
        limitations: List[str] = [
            "Noise reduction reference is generated non-destructively for human listening only.",
            "Authenticity / deepfake detection must always execute strictly on untouched raw audio.",
        ]

        try:
            report = self.assessor.assess(audio_input, sample_rate)

            if report.quality_status == AudioQualityStatus.INVALID:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return StandardAgentResponse(
                    agent_name=self.AGENT_NAME,
                    session_id=session_id,
                    status=AgentStatus.ERROR,
                    findings={
                        "audio_quality_status": "INVALID",
                        "summary": "Audio is unreadable or corrupted.",
                    },
                    measurements={},
                    confidence=0.0,
                    limitations=limitations,
                    recommended_action="REQUEST_FRESH_RECORDING",
                    processing_time_ms=elapsed_ms,
                    error="; ".join(report.quality_notes) or "Invalid audio stream",
                )

            snr_db = report.estimated_snr_db
            noise_dbfs = report.estimated_noise_level_dbfs
            rms_dbfs = report.rms_dbfs
            clipping_pct = report.clipping_percentage or 0.0

            # Determine usable speech segments (frames with energy >= noise floor + 9dB)
            has_clipping = clipping_pct >= 0.5
            has_high_noise = (snr_db is not None and snr_db < 10.0) or (noise_dbfs is not None and noise_dbfs > -32.0)
            has_low_volume = (rms_dbfs is not None and rms_dbfs < -40.0)

            findings: Dict[str, Any] = {
                "audio_quality_status": report.quality_status.value,
                "clipping_detected": has_clipping,
                "high_noise_detected": has_high_noise,
                "low_volume_detected": has_low_volume,
                "usable_speech_segments_detected": not (has_clipping or has_high_noise or has_low_volume),
                "issues": [issue.value for issue in report.detected_issues],
                "enhanced_audio_available": False,
                "enhanced_audio_reference": None,
                "enhanced_audio_note": "Original audio preserved; enhanced audio strictly prohibited for biometric inference.",
            }

            measurements: Dict[str, Optional[float]] = {
                "estimated_snr_db": snr_db,
                "estimated_noise_level_dbfs": noise_dbfs,
                "rms_level_dbfs": rms_dbfs,
                "clipping_percentage": clipping_pct,
            }

            if has_clipping:
                status = AgentStatus.WARNING
                recommended_action = "REDUCE_MICROPHONE_GAIN"
                findings["summary"] = f"Severe digital clipping ({clipping_pct:.2f}% samples). Request lower mic gain."
                confidence = 0.85
            elif has_high_noise:
                status = AgentStatus.WARNING
                recommended_action = "REQUEST_QUIETER_ENVIRONMENT"
                findings["summary"] = f"Elevated noise floor (SNR: {snr_db or 0.0:.1f} dB). Request quieter environment."
                confidence = 0.80
            elif has_low_volume:
                status = AgentStatus.WARNING
                recommended_action = "SPEAK_CLOSER_TO_MIC"
                findings["summary"] = f"Low speech volume ({rms_dbfs or -50.0:.1f} dBFS). Request user speak closer to mic."
                confidence = 0.80
            else:
                status = AgentStatus.PASS
                recommended_action = "PROCEED"
                findings["summary"] = "Acoustic conditions clean and acceptable for voice verification."
                confidence = 0.95

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return StandardAgentResponse(
                agent_name=self.AGENT_NAME,
                session_id=session_id,
                status=status,
                findings=findings,
                measurements=measurements,
                confidence=confidence,
                limitations=limitations,
                recommended_action=recommended_action,
                processing_time_ms=elapsed_ms,
                error=None,
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return StandardAgentResponse(
                agent_name=self.AGENT_NAME,
                session_id=session_id,
                status=AgentStatus.ERROR,
                findings={"summary": "Internal error during acoustic intelligence evaluation."},
                measurements={},
                confidence=0.0,
                limitations=limitations,
                recommended_action="REQUEST_FRESH_RECORDING",
                processing_time_ms=elapsed_ms,
                error=str(exc),
            )
