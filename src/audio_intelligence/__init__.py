"""
Audio Intelligence Public API.

Provides one simple public Python function `analyze_audio()` that Member 2 can import and call.
"""

from typing import Union, Optional, Dict, Any
import io
import numpy as np

from src.schemas import AudioQualityReport, AudioQualityThresholds
from src.audio_intelligence.assessor import AudioQualityAssessor


def analyze_audio(
    audio_input: Union[str, bytes, io.BytesIO, np.ndarray],
    sample_rate: Optional[int] = None,
    thresholds: Optional[AudioQualityThresholds] = None,
) -> AudioQualityReport:
    """
    Public entrypoint for Audio Intelligence Analysis (Phase 2).

    Parameters:
        audio_input: Path to audio file (str), byte stream (bytes / io.BytesIO),
                     or in-memory raw samples (np.ndarray).
        sample_rate: Optional sample rate in Hz. Required only if audio_input is np.ndarray.
        thresholds: Optional customized AudioQualityThresholds. If None, default provisional
                    hackathon thresholds are used.

    Returns:
        AudioQualityReport: Structured dataclass with all metrics, quality classification,
                            suitability flag, and recovery recommendations. Call .to_dict()
                            for JSON serialization.

    Example usage for Member 2:
        >>> from src.audio_intelligence import analyze_audio
        >>> report = analyze_audio("call_recording.wav")
        >>> if not report.suitable_for_authentication:
        ...     return {"status": "RETRY", "action": report.recommended_action.value}
    """
    assessor = AudioQualityAssessor(thresholds=thresholds)
    return assessor.assess(audio_input=audio_input, sample_rate=sample_rate)


__all__ = [
    "analyze_audio",
    "AudioQualityAssessor",
]
