"""
Audio Quality Assessor and Decision Rule Engine for Phase 2.

Classifies recordings into:
- GOOD
- MODERATE
- POOR
- INVALID

Generates explainable issues, recommended actions, and determines
whether the audio is suitable for downstream authentication analysis.

Strict invariant:
Audio quality alone NEVER authenticates a customer or determines genuineness.
Degraded audio prompts recovery or retry; it never bypasses verification.
"""

from typing import Union, Optional, List, Dict, Any, Tuple
import io
import numpy as np

from src.schemas import (
    AudioQualityReport,
    AudioQualityStatus,
    AudioQualityIssue,
    RecommendedAction,
    AudioQualityThresholds,
)
from src.audio_intelligence.loader import AudioValidator, AudioLoadError
from src.audio_intelligence.extractor import AudioFeatureExtractor


class AudioQualityAssessor:
    """
    Independent Audio Quality Assessor.
    Performs signal validation, frame-based feature extraction, quality classification,
    and adaptive recovery recommendations.
    """

    def __init__(self, thresholds: Optional[AudioQualityThresholds] = None):
        self.thresholds = thresholds or AudioQualityThresholds()
        self.validator = AudioValidator(self.thresholds)
        self.extractor = AudioFeatureExtractor()

    def assess(
        self,
        audio_input: Union[str, bytes, io.BytesIO, np.ndarray],
        sample_rate: Optional[int] = None,
    ) -> AudioQualityReport:
        """
        Main evaluation entrypoint.
        Accepts file paths, audio byte streams, or in-memory numpy arrays.
        """
        # Step 1: Validate & Load (with pre-downmix clipping detection)
        try:
            samples, sr, channels, pre_downmix_clip_pct = self.validator.load_audio(audio_input, sample_rate)
        except AudioLoadError as err:
            return self._build_invalid_report(err.issue, str(err))
        except Exception as err:
            return self._build_invalid_report(AudioQualityIssue.UNSUPPORTED_FORMAT, str(err))

        # Step 2: Extract Signal Features
        features = self.extractor.extract_features(samples, sr)
        duration = features["duration_seconds"]

        # Ensure clipping percentage accurately reflects pre-downmix channel saturation
        clipping_pct = max(features["clipping_percentage"] or 0.0, pre_downmix_clip_pct)

        # Step 3: Analyze issues against thresholds
        issues: List[AudioQualityIssue] = []
        notes: List[str] = []

        # Duration validation
        if duration < self.thresholds.min_duration_seconds:
            issues.append(AudioQualityIssue.INSUFFICIENT_DURATION)
            notes.append(f"Recording too short ({duration:.2f}s < {self.thresholds.min_duration_seconds}s).")
        elif duration > self.thresholds.max_duration_seconds:
            issues.append(AudioQualityIssue.EXCESSIVE_DURATION)
            notes.append(f"Recording exceeds maximum duration ({duration:.2f}s > {self.thresholds.max_duration_seconds}s).")

        # Clipping validation
        if clipping_pct >= self.thresholds.max_clipping_percentage:
            issues.append(AudioQualityIssue.AUDIO_CLIPPING)
            notes.append(f"Digital audio clipping detected ({clipping_pct:.2f}% of samples saturated).")

        # Low Volume validation (flag low volume if RMS < threshold, unless virtually zero energy -80 dBFS)
        rms_dbfs = features["rms_dbfs"]
        if rms_dbfs is not None and rms_dbfs < self.thresholds.min_rms_dbfs and rms_dbfs > -80.0:
            issues.append(AudioQualityIssue.LOW_RECORDING_VOLUME)
            notes.append(f"Low recording volume detected ({rms_dbfs:.1f} dBFS < {self.thresholds.min_rms_dbfs} dBFS).")

        # Noise & SNR validation
        # Only evaluate excessive noise if there was actual audio signal (not silence or extreme low volume)
        snr_db = features["estimated_snr_db"]
        noise_dbfs = features["estimated_noise_level_dbfs"]
        if rms_dbfs is not None and rms_dbfs >= self.thresholds.min_rms_dbfs:
            if (snr_db is not None and snr_db < self.thresholds.min_snr_db_moderate) or \
               (noise_dbfs is not None and noise_dbfs > self.thresholds.max_noise_level_dbfs):
                issues.append(AudioQualityIssue.EXCESSIVE_BACKGROUND_NOISE)
                notes.append(f"High background noise floor detected (SNR: {snr_db:.1f} dB, Noise: {noise_dbfs:.1f} dBFS).")

        # Speech duration and silence
        speech_sec = features["estimated_speech_duration_seconds"]
        silence_pct = features["silence_percentage"]
        if speech_sec is not None and speech_sec < self.thresholds.min_speech_duration_seconds:
            issues.append(AudioQualityIssue.INSUFFICIENT_SPEECH)
            notes.append(f"Insufficient active speech detected ({speech_sec:.2f}s < {self.thresholds.min_speech_duration_seconds}s).")
        
        if silence_pct is not None and silence_pct > self.thresholds.max_silence_percentage:
            issues.append(AudioQualityIssue.EXCESSIVE_SILENCE)
            notes.append(f"Excessive silence detected ({silence_pct:.1f}% > {self.thresholds.max_silence_percentage}%).")

        # Step 4: Classify Quality Status
        status, suitable = self._classify_status(issues, snr_db, duration)

        # Step 5: Adaptive Recommendation
        recommended_action = self._determine_recommendation(issues, status, rms_dbfs)

        if not notes:
            notes.append("Signal quality is clear with adequate active speech for biometric evaluation.")

        return AudioQualityReport(
            valid=True,
            quality_status=status,
            suitable_for_authentication=suitable,
            duration_seconds=duration,
            estimated_speech_duration_seconds=speech_sec,
            sample_rate=sr,
            channel_count=channels,
            estimated_noise_level_dbfs=noise_dbfs,
            estimated_snr_db=snr_db,
            silence_percentage=silence_pct,
            clipping_percentage=clipping_pct,
            rms_dbfs=rms_dbfs,
            peak_amplitude=features["peak_amplitude"],
            detected_issues=issues,
            recommended_action=recommended_action,
            quality_notes=notes,
        )

    def assess_array(self, audio_data: np.ndarray, sample_rate: int) -> AudioQualityReport:
        """Compatibility method for existing interfaces."""
        return self.assess(audio_data, sample_rate)

    def _classify_status(
        self,
        issues: List[AudioQualityIssue],
        snr_db: Optional[float],
        duration: float
    ) -> Tuple[AudioQualityStatus, bool]:
        """Classifies quality and biometric suitability."""
        # Fatal quality defects
        if (AudioQualityIssue.INSUFFICIENT_DURATION in issues or
            AudioQualityIssue.EXCESSIVE_DURATION in issues or
            AudioQualityIssue.INSUFFICIENT_SPEECH in issues):
            return AudioQualityStatus.POOR, False

        # Severe degradation
        severe_issues = {
            AudioQualityIssue.AUDIO_CLIPPING,
            AudioQualityIssue.EXCESSIVE_BACKGROUND_NOISE,
        }
        has_severe = any(issue in severe_issues for issue in issues)

        if has_severe:
            # If SNR is still acceptable (>= 8 dB) and no clipping, could be MODERATE
            if AudioQualityIssue.AUDIO_CLIPPING not in issues and snr_db is not None and snr_db >= self.thresholds.min_snr_db_moderate:
                return AudioQualityStatus.MODERATE, True
            return AudioQualityStatus.POOR, False

        # Moderate check (low volume or slight silence)
        if AudioQualityIssue.LOW_RECORDING_VOLUME in issues or AudioQualityIssue.EXCESSIVE_SILENCE in issues:
            return AudioQualityStatus.MODERATE, True

        if snr_db is not None and snr_db < self.thresholds.min_snr_db_good:
            return AudioQualityStatus.MODERATE, True

        return AudioQualityStatus.GOOD, True

    def _determine_recommendation(
        self,
        issues: List[AudioQualityIssue],
        status: AudioQualityStatus,
        rms_dbfs: Optional[float] = None,
    ) -> RecommendedAction:
        """Determines best recovery recommendation based on detected issues."""
        if status == AudioQualityStatus.GOOD:
            return RecommendedAction.PROCEED

        # Step 5: Adaptive Recommendation Priority:
        # 1. Total silence (virtual zero): ask for recording
        if rms_dbfs is not None and rms_dbfs <= -80.0:
            return RecommendedAction.REQUEST_LONGER_RECORDING

        # 2. Digital clipping: User needs to reduce mic sensitivity or speak further away
        if AudioQualityIssue.AUDIO_CLIPPING in issues:
            return RecommendedAction.REDUCE_MICROPHONE_GAIN

        # 3. Excessive background noise: Request quieter environment
        if AudioQualityIssue.EXCESSIVE_BACKGROUND_NOISE in issues:
            return RecommendedAction.REQUEST_QUIETER_ENVIRONMENT

        # 4. Low volume: Request speaking closer to mic
        if AudioQualityIssue.LOW_RECORDING_VOLUME in issues:
            return RecommendedAction.SPEAK_CLOSER_TO_MIC

        # 5. Short duration / excessive silence / insufficient speech
        if (AudioQualityIssue.EXCESSIVE_SILENCE in issues or
            AudioQualityIssue.INSUFFICIENT_SPEECH in issues or
            AudioQualityIssue.INSUFFICIENT_DURATION in issues):
            return RecommendedAction.REQUEST_LONGER_RECORDING

        if status == AudioQualityStatus.POOR or status == AudioQualityStatus.INVALID:
            return RecommendedAction.REQUEST_FRESH_RECORDING

        return RecommendedAction.PROCEED

    def _build_invalid_report(self, issue: AudioQualityIssue, message: str) -> AudioQualityReport:
        """Constructs a deterministic INVALID report for corrupt/missing inputs."""
        return AudioQualityReport(
            valid=False,
            quality_status=AudioQualityStatus.INVALID,
            suitable_for_authentication=False,
            duration_seconds=0.0,
            estimated_speech_duration_seconds=None,
            sample_rate=None,
            channel_count=None,
            estimated_noise_level_dbfs=None,
            estimated_snr_db=None,
            silence_percentage=None,
            clipping_percentage=None,
            rms_dbfs=None,
            peak_amplitude=None,
            detected_issues=[issue],
            recommended_action=RecommendedAction.REQUEST_FRESH_RECORDING,
            quality_notes=[f"Audio input invalid: {message}"],
        )
