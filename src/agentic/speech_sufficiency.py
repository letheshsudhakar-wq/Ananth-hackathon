"""
src/agentic/speech_sufficiency.py — Agent 1: Speech Sufficiency Agent.

Objective:
Handle short voice recordings intelligently.
Calculates actual usable speech duration using frame energy / VAD, detects silence and non-speech,
manages session-based accumulation of speech chunks, and recommends collecting additional speech
rather than rejecting the customer outright when speech is insufficient.
"""

from __future__ import annotations

import time
import math
from typing import Dict, Any, Optional, List, Union
import numpy as np

from src.schemas import AudioQualityStatus, AudioQualityIssue
from src.audio_intelligence.assessor import AudioQualityAssessor
from src.audio_intelligence.loader import AudioValidator
from src.agentic.schemas import StandardAgentResponse, AgentStatus


class SpeechSufficiencyAgent:
    """Agent 1: Determines if spoken voice duration satisfies Detectif.ai minimum thresholds."""

    AGENT_NAME = "speech_sufficiency_agent"
    DEFAULT_MIN_SPEECH_SECONDS = 1.8  # Detectif recommended usable voice duration
    DEFAULT_MIN_TOTAL_SECONDS = 2.0

    def __init__(
        self,
        min_speech_seconds: float = DEFAULT_MIN_SPEECH_SECONDS,
        assessor: Optional[AudioQualityAssessor] = None,
    ):
        self.min_speech_seconds = min_speech_seconds
        self.assessor = assessor or AudioQualityAssessor()
        # Session speech accumulation store: session_id -> accumulated usable seconds
        self._session_speech_store: Dict[str, float] = {}

    def reset_session(self, session_id: str) -> None:
        self._session_speech_store.pop(session_id, None)

    def _compute_usable_speech_seconds(
        self,
        audio_input: Union[str, bytes, np.ndarray],
        sample_rate: Optional[int],
        noise_floor_dbfs: Optional[float],
    ) -> Optional[float]:
        """
        Frame-energy based usable-speech duration (VAD heuristic, 25ms frames, 10ms hop).
        Reuses the existing AudioValidator for ingestion; independent from the
        assessor threshold so sufficiency detection is not blocked by the
        assessor's conservative POOR classification.
        """
        try:
            samples, sr, _, _ = AudioValidator().load_audio(audio_input, sample_rate)
        except Exception:
            return None
        if sr <= 0 or len(samples) < 160:
            return 0.0
        frame_len = max(int(0.025 * sr), 16)
        hop = max(int(0.010 * sr), 8)
        if len(samples) < frame_len:
            return 0.0
        num_frames = 1 + (len(samples) - frame_len) // hop
        frames = np.lib.stride_tricks.as_strided(
            samples, shape=(num_frames, frame_len), strides=(samples.strides[0] * hop, samples.strides[0])
        )
        frame_dbfs = 20.0 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-12)
        floor = noise_floor_dbfs if noise_floor_dbfs is not None else float(np.percentile(frame_dbfs, 12))
        threshold = max(floor + 3.0, -50.0)
        speech_frames = int(np.sum(frame_dbfs >= threshold))
        return float(speech_frames * hop) / float(sr)

    def analyze(
        self,
        session_id: str,
        audio_input: Union[str, bytes, np.ndarray],
        sample_rate: Optional[int] = None,
        accumulate: bool = True,
    ) -> StandardAgentResponse:
        # Default sample rate for numpy arrays so the assessor doesn't reject them
        if isinstance(audio_input, np.ndarray) and sample_rate is None:
            sample_rate = 16000
        t0 = time.perf_counter()
        limitations: List[str] = [
            "Voice activity uses frame-energy thresholding heuristics without certified acoustic phonetic segmentation.",
            "Silence or breathing may introduce minor speech boundary variance (+-50ms).",
        ]

        try:
            report = self.assessor.assess(audio_input, sample_rate)

            # Handle invalid / corrupted inputs
            if report.quality_status == AudioQualityStatus.INVALID:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return StandardAgentResponse(
                    agent_name=self.AGENT_NAME,
                    session_id=session_id,
                    status=AgentStatus.ERROR,
                    findings={
                        "speech_sufficiency_status": "AUDIO_INVALID",
                        "issues": [issue.value for issue in report.detected_issues],
                        "summary": "Audio could not be decoded or is structurally invalid.",
                    },
                    measurements={
                        "total_duration_seconds": 0.0,
                        "usable_speech_duration_seconds": 0.0,
                        "accumulated_speech_seconds": self._session_speech_store.get(session_id, 0.0),
                    },
                    confidence=0.0,
                    limitations=limitations,
                    recommended_action="REQUEST_FRESH_RECORDING",
                    processing_time_ms=elapsed_ms,
                    error="; ".join(report.quality_notes) or "Audio invalid",
                )

            total_duration = report.duration_seconds or 0.0
            assessor_speech_duration = report.estimated_speech_duration_seconds
            silence_pct = report.silence_percentage or 0.0
            # Actual usable-speech duration from frame-energy VAD
            raw_speech_duration = self._compute_usable_speech_seconds(
                audio_input, sample_rate, report.estimated_noise_level_dbfs
            )
            if raw_speech_duration is None:
                raw_speech_duration = assessor_speech_duration or 0.0

            # Accumulate usable speech across multi-turn prompts if requested
            prev_accumulated = self._session_speech_store.get(session_id, 0.0)
            current_accumulated = prev_accumulated + raw_speech_duration if accumulate else raw_speech_duration
            if accumulate:
                self._session_speech_store[session_id] = current_accumulated

            # Decision logic
            if current_accumulated >= self.min_speech_seconds:
                status = AgentStatus.PASS
                recommended_action = "PROCEED"
                findings_summary = (
                    f"Speech duration sufficient ({current_accumulated:.2f}s usable speech, "
                    f"threshold: {self.min_speech_seconds:.2f}s)."
                )
                confidence = min(1.0, 0.70 + (current_accumulated / (self.min_speech_seconds * 2.0)) * 0.30)
            else:
                deficit = self.min_speech_seconds - current_accumulated
                status = AgentStatus.WARNING
                recommended_action = "COLLECT_ADDITIONAL_SPEECH"
                findings_summary = (
                    f"Speech duration insufficient ({current_accumulated:.2f}s usable speech vs "
                    f"{self.min_speech_seconds:.2f}s needed; {deficit:.2f}s additional speech required)."
                )
                confidence = max(0.50, current_accumulated / self.min_speech_seconds)

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return StandardAgentResponse(
                agent_name=self.AGENT_NAME,
                session_id=session_id,
                status=status,
                findings={
                    "speech_sufficiency_status": "SUFFICIENT" if status == AgentStatus.PASS else "INSUFFICIENT",
                    "total_duration_seconds": round(total_duration, 3),
                    "usable_speech_duration_seconds": round(raw_speech_duration, 3),
                    "accumulated_speech_seconds": round(current_accumulated, 3),
                    "silence_percentage": round(silence_pct, 1),
                    "deficit_seconds": max(0.0, round(self.min_speech_seconds - current_accumulated, 3)),
                    "confidence_reliability": round(confidence, 3),
                    "summary": findings_summary,
                },
                measurements={
                    "total_duration_seconds": total_duration,
                    "usable_speech_duration_seconds": raw_speech_duration,
                    "accumulated_speech_seconds": current_accumulated,
                    "silence_percentage": silence_pct,
                },
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
                findings={"summary": "Internal error during speech sufficiency evaluation."},
                measurements={},
                confidence=0.0,
                limitations=limitations,
                recommended_action="REQUEST_FRESH_RECORDING",
                processing_time_ms=elapsed_ms,
                error=str(exc),
            )
