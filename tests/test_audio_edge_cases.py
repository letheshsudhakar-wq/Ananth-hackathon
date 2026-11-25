"""
Advanced Synthetic Audio Edge Case Tests (Task 2).

Generates reproducible synthetic waveforms using deterministic fixed seeds:
- White noise, simulated traffic noise, crowd noise, intermittent bursts
- High volume, low volume, silence, long silence intervals
- Opposite-phase stereo channel cancellation defense
- Oversized decoded audio arrays
- Different sample rates (8kHz, 16kHz, 44.1kHz, 48kHz)
"""

import pytest
import numpy as np
import soundfile as sf
import io

from src.schemas import (
    AudioQualityStatus,
    AudioQualityIssue,
    RecommendedAction,
)
from src.audio_intelligence import analyze_audio


def _generate_synthetic_tone(
    duration: float = 3.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
    amplitude: float = 0.5,
) -> np.ndarray:
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def test_audio_edge_white_noise():
    """Deterministic high-level white noise signal without digital clipping."""
    np.random.seed(1001)
    sample_rate = 16000
    # Scaled normal noise with peak well below 1.0 (sigma=0.2)
    noise = np.random.normal(0, 0.2, sample_rate * 3).astype(np.float32)
    report = analyze_audio(noise, sample_rate=sample_rate)
    assert report.valid is True
    assert AudioQualityIssue.EXCESSIVE_BACKGROUND_NOISE in report.detected_issues
    assert report.recommended_action == RecommendedAction.REQUEST_QUIETER_ENVIRONMENT


def test_audio_edge_simulated_traffic_noise():
    """Simulated low-frequency rumbling traffic noise (60-120 Hz rumble)."""
    np.random.seed(1002)
    sample_rate = 16000
    t = np.linspace(0, 3.0, sample_rate * 3, endpoint=False)
    rumble = 0.3 * np.sin(2 * np.pi * 65.0 * t) + 0.2 * np.sin(2 * np.pi * 110.0 * t)
    noise = np.random.normal(0, 0.15, sample_rate * 3)
    traffic_audio = (rumble + noise).astype(np.float32)
    
    report = analyze_audio(traffic_audio, sample_rate=sample_rate)
    assert report.valid is True
    assert AudioQualityIssue.EXCESSIVE_BACKGROUND_NOISE in report.detected_issues


def test_audio_edge_simulated_crowd_babble():
    """Simulated multi-frequency crowd babble background with weak speech."""
    np.random.seed(1003)
    sample_rate = 16000
    t = np.linspace(0, 3.0, sample_rate * 3, endpoint=False)
    babble = sum(0.08 * np.sin(2 * np.pi * f * t) for f in [210, 350, 480, 620, 800])
    audio = (babble + np.random.normal(0, 0.1, sample_rate * 3)).astype(np.float32)

    report = analyze_audio(audio, sample_rate=sample_rate)
    assert report.valid is True
    assert report.suitable_for_authentication is False or report.quality_status in (AudioQualityStatus.POOR, AudioQualityStatus.MODERATE)


def test_audio_edge_intermittent_noise():
    """Speech with loud intermittent transient noise spikes."""
    np.random.seed(1004)
    sample_rate = 16000
    t = np.linspace(0, 3.0, sample_rate * 3, endpoint=False)
    speech = 0.4 * np.sin(2 * np.pi * 300 * t)
    # Inject 3 loud spikes
    speech[int(0.5 * sample_rate):int(0.55 * sample_rate)] += 0.8
    speech[int(1.5 * sample_rate):int(1.55 * sample_rate)] += 0.8
    speech[int(2.5 * sample_rate):int(2.55 * sample_rate)] += 0.8
    clipped = np.clip(speech, -1.0, 1.0).astype(np.float32)

    report = analyze_audio(clipped, sample_rate=sample_rate)
    assert report.valid is True
    assert report.clipping_percentage is not None


def test_audio_edge_long_silent_intervals():
    """Audio with brief pulse and 80%+ trailing silence."""
    sample_rate = 16000
    audio = np.zeros(sample_rate * 4, dtype=np.float32)
    # 0.5s sound at start, rest 3.5s pure silence
    t = np.linspace(0, 0.5, int(0.5 * sample_rate), endpoint=False)
    audio[0:len(t)] = 0.5 * np.sin(2 * np.pi * 400 * t)

    report = analyze_audio(audio, sample_rate=sample_rate)
    assert report.valid is True
    assert AudioQualityIssue.INSUFFICIENT_SPEECH in report.detected_issues or AudioQualityIssue.EXCESSIVE_SILENCE in report.detected_issues
    assert report.suitable_for_authentication is False


def test_audio_edge_opposite_phase_stereo_cancellation():
    """
    Opposite-Phase Stereo Anti-Cancellation Defense:
    Left channel = Signal, Right channel = -Signal.
    Standard averaging yields 0 (silent), falsely flagging good audio as silent.
    Engine must detect anti-phase cancellation and preserve signal integrity.
    """
    sample_rate = 16000
    t = np.linspace(0, 3.0, sample_rate * 3, endpoint=False)
    signal = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    stereo_anti_phase = np.stack([signal, -signal], axis=1)

    report = analyze_audio(stereo_anti_phase, sample_rate=sample_rate)
    assert report.valid is True
    # Successfully avoided cancellation to dead silence
    assert report.rms_dbfs is not None and report.rms_dbfs > -30.0
    assert report.channel_count == 2


@pytest.mark.parametrize("sr", [8000, 16000, 44100, 48000])
def test_audio_edge_supported_sample_rates(sr):
    """Test standard telephony and VoIP rates."""
    audio = _generate_synthetic_tone(duration=2.0, sample_rate=sr)
    report = analyze_audio(audio, sample_rate=sr)
    assert report.valid is True
    assert report.sample_rate == sr
    assert report.duration_seconds == 2.0


def test_audio_edge_oversized_audio_buffer():
    """Rejects excessively large decoded audio arrays before heavy processing."""
    sample_rate = 16000
    # Create oversized array (> 2 * max_duration limit)
    oversized = np.zeros(sample_rate * 70, dtype=np.float32)
    report = analyze_audio(oversized, sample_rate=sample_rate)
    assert report.valid is False
    assert AudioQualityIssue.EXCESSIVE_DURATION in report.detected_issues
