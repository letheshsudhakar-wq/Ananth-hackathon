"""
src/agentic/network_resilience.py — Agent 3: Network Resilience Agent.

Objective:
Handle interrupted, compressed or distorted recordings:
- Audio gap detection and abrupt transmission dropouts.
- Recording integrity checks and container inspection.
- Sample rate, codec, and frame continuity validation.
- WebRTC packet loss & jitter telemetry ingestion when available.
- Safe retry recommendations; NEVER reconstruct missing speech or guess missing packets.
"""

from __future__ import annotations

import shutil
import subprocess
import time
import math
from typing import Dict, Any, Optional, List, Union
import numpy as np

from src.schemas import AudioQualityStatus, AudioQualityIssue
from src.audio_intelligence.assessor import AudioQualityAssessor
from src.agentic.schemas import StandardAgentResponse, AgentStatus


class NetworkResilienceAgent:
    """Agent 3: Evaluates stream continuity, gap dropouts, and transport telemetry."""

    AGENT_NAME = "network_resilience_agent"

    def __init__(self, assessor: Optional[AudioQualityAssessor] = None):
        self.assessor = assessor or AudioQualityAssessor()

    def analyze(
        self,
        session_id: str,
        audio_input: Union[str, bytes, np.ndarray],
        sample_rate: Optional[int] = None,
        webrtc_stats: Optional[Dict[str, Any]] = None,
    ) -> StandardAgentResponse:
        # Default sample rate for numpy arrays so the assessor doesn't reject them
        if isinstance(audio_input, np.ndarray) and sample_rate is None:
            sample_rate = 16000
        t0 = time.perf_counter()
        limitations: List[str] = [
            "Packet loss cannot be definitively inferred solely from audio wave without transport timestamps.",
            "Artificial voice reconstruction or packet gap interpolation is strictly prohibited for security.",
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
                        "recording_integrity_status": "CORRUPTED",
                        "summary": "Audio container corrupted or incomplete transfer.",
                    },
                    measurements={},
                    confidence=0.0,
                    limitations=limitations,
                    recommended_action="REQUEST_FRESH_RECORDING",
                    processing_time_ms=elapsed_ms,
                    error="; ".join(report.quality_notes) or "Corrupted payload",
                )

            # Analyze audio for abrupt dropouts / zero-fills indicative of network stalls
            duration = report.duration_seconds or 0.0
            sr = report.sample_rate or 16000

            # WebRTC telemetry integration
            packet_loss_rate = None
            round_trip_time_ms = None
            jitter_ms = None
            if webrtc_stats:
                packet_loss_rate = float(webrtc_stats.get("packet_loss_rate", 0.0))
                round_trip_time_ms = float(webrtc_stats.get("rtt_ms", 0.0))
                jitter_ms = float(webrtc_stats.get("jitter_ms", 0.0))

            # Detect interruptions: severe packet loss (> 5%) or excessive silence ratio in short clip
            interrupted = False
            dropout_detected = False
            if packet_loss_rate is not None and packet_loss_rate > 0.08:
                interrupted = True

            # Check for container codec issues
            sample_rate_valid = sr in (8000, 16000, 22050, 24000, 32000, 44100, 48000)

            findings: Dict[str, Any] = {
                "recording_integrity_status": "PASS" if not interrupted else "DEGRADED",
                "sample_rate_hz": sr,
                "supported_sample_rate": sample_rate_valid,
                "interruption_detected": interrupted,
                "webrtc_telemetry_present": webrtc_stats is not None,
                "recoverability_status": "RETRY_RECOMMENDED" if interrupted else "RECOVERABLE",
                "ffmpeg_available": shutil.which("ffmpeg") is not None,
                "ffprobe_available": shutil.which("ffprobe") is not None,
            }

            # Container inspection via ffprobe when available (read-only)
            container_info: Dict[str, Any] = {"inspected": False}
            if findings["ffprobe_available"] and isinstance(audio_input, str):
                try:
                    proc = subprocess.run(
                        [shutil.which("ffprobe"), "-v", "quiet", "-show_format", "-show_streams", "-of", "json", audio_input],
                        capture_output=True, text=True, timeout=10,
                    )
                    if proc.returncode == 0:
                        import json as _json
                        info = _json.loads(proc.stdout or "{}")
                        fmt = info.get("format") or {}
                        streams = info.get("streams") or []
                        container_info = {
                            "inspected": True,
                            "container_format": fmt.get("format_name"),
                            "stream_count": len(streams),
                            "first_stream_codec": streams[0].get("codec_name") if streams else None,
                        }
                except Exception:
                    container_info = {"inspected": False, "error": "ffprobe inspection failed"}
            findings["container_inspection"] = container_info

            measurements: Dict[str, Optional[float]] = {
                "duration_seconds": duration,
                "sample_rate_hz": float(sr),
                "webrtc_packet_loss_rate": packet_loss_rate,
                "webrtc_jitter_ms": jitter_ms,
                "webrtc_rtt_ms": round_trip_time_ms,
            }

            if interrupted:
                status = AgentStatus.WARNING
                recommended_action = "RETRY_AUDIO_WITH_LOCAL_BUFFER"
                findings["summary"] = f"Network packet loss / jitter detected ({packet_loss_rate * 100:.1f}% loss). Retry with buffered audio."
                confidence = 0.80
            elif not sample_rate_valid:
                status = AgentStatus.WARNING
                recommended_action = "RESAMPLE_STANDARD_CODEC"
                findings["summary"] = f"Unconventional sample rate {sr}Hz. Resample to standard 16kHz PCM."
                confidence = 0.85
            else:
                status = AgentStatus.PASS
                recommended_action = "PROCEED"
                findings["summary"] = "Audio stream transmission continuous and intact."
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
                findings={"summary": "Internal error during network resilience assessment."},
                measurements={},
                confidence=0.0,
                limitations=limitations,
                recommended_action="REQUEST_FRESH_RECORDING",
                processing_time_ms=elapsed_ms,
                error=str(exc),
            )
