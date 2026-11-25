"""
Comprehensive Automated Test Suite for Phase 2 Audio Intelligence Engine.

Generates all synthetic signals programmatically without storing private customer recordings.
Tests:
1. Clean signal.
2. Noisy signal.
3. Silent recording.
4. Short recording.
5. Clipped recording.
6. Low-volume recording.
7. Stereo recording.
8. Corrupted file.
9. Unsupported input.
10. Missing file.
11. Phase 1 compatibility & security rule invariant.
"""

import os
import io
import pytest
import numpy as np
import soundfile as sf

from src.schemas import (
    AudioQualityStatus,
    AudioQualityIssue,
    RecommendedAction,
    AudioQualityReport,
    TrustDecision,
    VerificationStatus,
)
from src.audio_intelligence import analyze_audio, AudioQualityAssessor
from src.trust_engine.engine import AdaptiveTrustEngine
from src.trust_engine.mock_data import MockDataFactory


@pytest.fixture
def tmp_audio_dir(tmp_path):
    """Fixture to provide a clean temporary folder for synthetic files."""
    return tmp_path


def _generate_synthetic_speech_like_signal(
    duration: float = 3.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
    noise_level: float = 0.005,
    burst_intervals: list = None,
) -> np.ndarray:
    """
    Synthesizes a periodic burst signal simulating speech pulses against a quiet background.
    """
    total_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    
    # Ambient background noise
    np.random.seed(42)
    noise = np.random.normal(0, noise_level, total_samples).astype(np.float32)

    # Periodic speech harmonic pulses (simulating vocal formants)
    signal = np.zeros(total_samples, dtype=np.float32)
    carrier = (0.6 * np.sin(2 * np.pi * 220 * t) + 
               0.3 * np.sin(2 * np.pi * 440 * t) + 
               0.1 * np.sin(2 * np.pi * 880 * t)).astype(np.float32) * amplitude

    if burst_intervals is None:
        # Default: speech active for 70% of duration (two 1-second bursts)
        burst_intervals = [(0.2, 1.4), (1.7, 2.8)]

    for start, end in burst_intervals:
        idx_start = int(start * sample_rate)
        idx_end = min(int(end * sample_rate), total_samples)
        if idx_start < idx_end:
            signal[idx_start:idx_end] = carrier[idx_start:idx_end]

    return np.clip(signal + noise, -1.0, 1.0)


# ==============================================================================
# TEST SUITE
# ==============================================================================

def test_1_clean_signal(tmp_audio_dir):
    """Test clean audio with sufficient speech and low noise."""
    samples = _generate_synthetic_speech_like_signal(duration=3.0, amplitude=0.5, noise_level=0.002)
    file_path = str(tmp_audio_dir / "clean.wav")
    sf.write(file_path, samples, 16000)

    report = analyze_audio(file_path)
    assert report.valid is True
    assert report.quality_status == AudioQualityStatus.GOOD
    assert report.suitable_for_authentication is True
    assert report.recommended_action == RecommendedAction.PROCEED
    assert report.estimated_snr_db is not None and report.estimated_snr_db > 15.0
    assert report.clipping_percentage == 0.0
    assert report.channel_count == 1


def test_2_noisy_signal(tmp_audio_dir):
    """Test signal with high ambient noise."""
    samples = _generate_synthetic_speech_like_signal(duration=3.0, amplitude=0.2, noise_level=0.15)
    file_path = str(tmp_audio_dir / "noisy.wav")
    sf.write(file_path, samples, 16000)

    report = analyze_audio(file_path)
    assert report.valid is True
    assert AudioQualityIssue.EXCESSIVE_BACKGROUND_NOISE in report.detected_issues
    assert report.recommended_action == RecommendedAction.REQUEST_QUIETER_ENVIRONMENT
    assert report.estimated_snr_db is not None and report.estimated_snr_db < 15.0


def test_3_silent_recording(tmp_audio_dir):
    """Test completely silent audio (zero amplitude)."""
    samples = np.zeros(16000 * 3, dtype=np.float32)
    file_path = str(tmp_audio_dir / "silent.wav")
    sf.write(file_path, samples, 16000)

    report = analyze_audio(file_path)
    assert report.valid is True
    assert report.quality_status == AudioQualityStatus.POOR
    assert report.suitable_for_authentication is False
    assert AudioQualityIssue.INSUFFICIENT_SPEECH in report.detected_issues
    assert AudioQualityIssue.EXCESSIVE_SILENCE in report.detected_issues
    assert report.recommended_action == RecommendedAction.REQUEST_LONGER_RECORDING


def test_4_short_recording(tmp_audio_dir):
    """Test recording below minimum duration threshold (e.g. 0.4s)."""
    samples = _generate_synthetic_speech_like_signal(duration=0.4, burst_intervals=[(0.0, 0.3)])
    file_path = str(tmp_audio_dir / "short.wav")
    sf.write(file_path, samples, 16000)

    report = analyze_audio(file_path)
    assert report.valid is True
    assert report.quality_status == AudioQualityStatus.POOR
    assert report.suitable_for_authentication is False
    assert AudioQualityIssue.INSUFFICIENT_DURATION in report.detected_issues
    assert report.recommended_action == RecommendedAction.REQUEST_LONGER_RECORDING


def test_5_clipped_recording(tmp_audio_dir):
    """Test audio with harsh digital clipping (saturated amplitudes)."""
    samples = _generate_synthetic_speech_like_signal(duration=3.0, amplitude=3.0)
    samples = np.clip(samples, -1.0, 1.0)  # Heavy digital saturation
    file_path = str(tmp_audio_dir / "clipped.wav")
    sf.write(file_path, samples, 16000)

    report = analyze_audio(file_path)
    assert report.valid is True
    assert AudioQualityIssue.AUDIO_CLIPPING in report.detected_issues
    assert report.clipping_percentage > 1.0
    assert report.suitable_for_authentication is False
    assert report.recommended_action == RecommendedAction.REDUCE_MICROPHONE_GAIN


def test_6_low_volume_recording(tmp_audio_dir):
    """Test recording with very weak signal / low microphone gain."""
    samples = _generate_synthetic_speech_like_signal(duration=3.0, amplitude=0.002, noise_level=0.0001)
    file_path = str(tmp_audio_dir / "low_volume.wav")
    sf.write(file_path, samples, 16000)

    report = analyze_audio(file_path)
    assert report.valid is True
    assert AudioQualityIssue.LOW_RECORDING_VOLUME in report.detected_issues
    assert report.recommended_action == RecommendedAction.SPEAK_CLOSER_TO_MIC


def test_7_stereo_recording(tmp_audio_dir):
    """Test 2-channel stereo audio is ingested cleanly without breaking channel count reporting."""
    mono_left = _generate_synthetic_speech_like_signal(duration=2.5, amplitude=0.4)
    mono_right = _generate_synthetic_speech_like_signal(duration=2.5, amplitude=0.4)
    stereo_samples = np.stack([mono_left, mono_right], axis=1)

    file_path = str(tmp_audio_dir / "stereo.wav")
    sf.write(file_path, stereo_samples, 16000)

    report = analyze_audio(file_path)
    assert report.valid is True
    assert report.channel_count == 2
    assert report.suitable_for_authentication is True
    assert report.quality_status == AudioQualityStatus.GOOD


def test_8_corrupted_file(tmp_audio_dir):
    """Test handling of invalid/corrupt audio binary file."""
    corrupt_path = str(tmp_audio_dir / "corrupted.wav")
    with open(corrupt_path, "wb") as f:
        f.write(b"RIFF\x00\x00\x00\x00NOT_VALID_AUDIO_DATA_AT_ALL")

    report = analyze_audio(corrupt_path)
    assert report.valid is False
    assert report.quality_status == AudioQualityStatus.INVALID
    assert report.suitable_for_authentication is False
    assert AudioQualityIssue.FILE_CORRUPTED in report.detected_issues
    assert report.recommended_action == RecommendedAction.REQUEST_FRESH_RECORDING


def test_9_unsupported_input():
    """Test handling of completely unsupported input type."""
    report = analyze_audio(123456)  # invalid integer type
    assert report.valid is False
    assert report.quality_status == AudioQualityStatus.INVALID
    assert report.suitable_for_authentication is False
    assert AudioQualityIssue.UNSUPPORTED_FORMAT in report.detected_issues


def test_10_missing_file():
    """Test handling of non-existent audio file path."""
    report = analyze_audio("c:/non_existent_directory_987654321/ghost_file.wav")
    assert report.valid is False
    assert report.quality_status == AudioQualityStatus.INVALID
    assert report.suitable_for_authentication is False
    assert AudioQualityIssue.FILE_MISSING in report.detected_issues
    assert report.recommended_action == RecommendedAction.REQUEST_FRESH_RECORDING


def test_11_in_memory_bytes_and_numpy():
    """Test that analyze_audio supports in-memory bytes and direct numpy arrays."""
    samples = _generate_synthetic_speech_like_signal(duration=2.0, amplitude=0.5)

    # In-memory numpy array test
    report_np = analyze_audio(samples, sample_rate=16000)
    assert report_np.valid is True
    assert report_np.quality_status == AudioQualityStatus.GOOD

    # In-memory BytesIO WAV buffer test
    buffer = io.BytesIO()
    sf.write(buffer, samples, 16000, format="WAV")
    buffer.seek(0)
    report_bytes = analyze_audio(buffer.read())
    assert report_bytes.valid is True
    assert report_bytes.quality_status == AudioQualityStatus.GOOD


def test_12_non_finite_samples():
    """Test that NaN and Inf samples are caught as invalid."""
    samples = np.array([0.1, np.nan, 0.5, np.inf], dtype=np.float32)
    report = analyze_audio(samples, sample_rate=16000)
    assert report.valid is False
    assert AudioQualityIssue.NON_FINITE_SAMPLES in report.detected_issues


def test_13_trust_engine_integration_and_golden_rule():
    """
    Invariant check: Audio quality alone must NEVER weaken or authenticate a caller.
    """
    engine = AdaptiveTrustEngine()
    
    # 1. Even with perfect audio, a low liveness/voice match score must not pass
    evidence, _ = MockDataFactory.get_deepfake_attack_caller()
    perfect_audio = AudioQualityReport(
        valid=True,
        quality_status=AudioQualityStatus.GOOD,
        suitable_for_authentication=True,
        duration_seconds=4.0,
        estimated_speech_duration_seconds=3.5,
        sample_rate=16000,
        channel_count=1,
        estimated_noise_level_dbfs=-60.0,
        estimated_snr_db=30.0,
        silence_percentage=10.0,
        clipping_percentage=0.0,
        rms_dbfs=-20.0,
        peak_amplitude=0.7,
        detected_issues=[],
        recommended_action=RecommendedAction.PROCEED,
    )
    res = engine.evaluate(evidence, perfect_audio)
    # Liveness is 0.12, so composite score must not satisfy trust threshold
    assert res.composite_trust_score < 0.75

    # 2. When audio is unsuitable, it triggers RETRY_AUDIO unless a credible attack escalates it to DENY
    # Here evidence is a deepfake attack (aletheia_liveness=0.12), so Task 2 / Rule 1 dictates DENY (attack escalation)
    _, bad_audio = MockDataFactory.get_unusable_audio_caller()
    res_bad = engine.evaluate(evidence, bad_audio)
    assert res_bad.decision == TrustDecision.DENY
    assert res_bad.verification_status == VerificationStatus.SUSPICIOUS

    # 3. For an innocent caller with bad audio, it correctly prompts RETRY_AUDIO
    clean_ev, _ = MockDataFactory.get_clean_legitimate_caller()
    res_retry = engine.evaluate(clean_ev, bad_audio)
    assert res_retry.decision == TrustDecision.RETRY_AUDIO
    assert res_retry.audio_degradation_detected is True
