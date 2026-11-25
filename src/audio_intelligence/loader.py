"""
Audio Loader and Validator Module.

Handles:
- Missing files
- Empty recordings
- Corrupted audio
- Unsupported formats
- File size guardrails
- Non-finite samples (NaN, Inf)
- Mono and stereo conversion (without modifying original file)
"""

import os
from typing import Tuple, Optional, List, Union
import io
import numpy as np
import soundfile as sf

from src.schemas import (
    AudioQualityIssue,
    AudioQualityThresholds,
)


class AudioLoadError(Exception):
    """Custom exception raised when audio cannot be loaded or is fundamentally invalid."""
    def __init__(self, issue: AudioQualityIssue, message: str):
        super().__init__(message)
        self.issue = issue
        self.message = message


class AudioValidator:
    """Validates and safely ingests raw audio inputs without altering original files."""

    def __init__(self, thresholds: Optional[AudioQualityThresholds] = None):
        self.thresholds = thresholds or AudioQualityThresholds()

    def load_audio(
        self,
        audio_input: Union[str, bytes, io.BytesIO, np.ndarray],
        sample_rate: Optional[int] = None,
    ) -> Tuple[np.ndarray, int, int, float]:
        """
        Loads and validates audio input.

        Returns:
            Tuple of:
            - mono_samples: np.ndarray (float32, normalized -1.0 to 1.0)
            - sample_rate: int
            - original_channels: int (1 for mono, 2 for stereo, etc.)
            - pre_downmix_clipping_percentage: float

        Raises:
            AudioLoadError: If input is missing, empty, corrupt, unsupported, or invalid.
        """
        # Case A: In-memory numpy array passed directly
        if isinstance(audio_input, np.ndarray):
            if sample_rate is None or sample_rate <= 0:
                raise AudioLoadError(
                    AudioQualityIssue.INVALID_SAMPLE_RATE,
                    "A valid positive sample_rate must be provided when passing a numpy array."
                )
            if audio_input.size == 0:
                raise AudioLoadError(
                    AudioQualityIssue.FILE_EMPTY,
                    "Audio buffer is empty."
                )
            total_samples = audio_input.shape[0] if audio_input.ndim >= 1 else 0
            if total_samples > (self.thresholds.max_duration_seconds * sample_rate * 2):
                raise AudioLoadError(
                    AudioQualityIssue.EXCESSIVE_DURATION,
                    f"Audio array contains excessive samples ({total_samples} > {self.thresholds.max_duration_seconds * sample_rate * 2})."
                )
            return self._sanitize_array(audio_input, sample_rate)

        # Case B: File path provided
        if isinstance(audio_input, str):
            if not os.path.exists(audio_input):
                raise AudioLoadError(
                    AudioQualityIssue.FILE_MISSING,
                    f"Audio file not found at path: {audio_input}"
                )
            
            file_size = os.path.getsize(audio_input)
            if file_size == 0:
                raise AudioLoadError(
                    AudioQualityIssue.FILE_EMPTY,
                    f"Audio file is empty (0 bytes): {audio_input}"
                )
            if file_size > self.thresholds.max_file_size_bytes:
                raise AudioLoadError(
                    AudioQualityIssue.EXCESSIVE_DURATION,
                    f"File exceeds maximum allowed size ({file_size} > {self.thresholds.max_file_size_bytes} bytes)."
                )

            try:
                data, sr = sf.read(audio_input, dtype="float32", always_2d=False)
            except sf.LibsndfileError as err:
                raise AudioLoadError(
                    AudioQualityIssue.FILE_CORRUPTED,
                    f"Failed to decode audio file (unsupported format or corrupted): {str(err)}"
                ) from err
            except Exception as err:
                raise AudioLoadError(
                    AudioQualityIssue.UNSUPPORTED_FORMAT,
                    f"Unsupported audio format or loader failure: {str(err)}"
                ) from err

            return self._sanitize_array(data, sr)

        # Case C: Bytes or BytesIO
        if isinstance(audio_input, (bytes, io.BytesIO)):
            bio = io.BytesIO(audio_input) if isinstance(audio_input, bytes) else audio_input
            bio.seek(0, io.SEEK_END)
            size = bio.tell()
            bio.seek(0)

            if size == 0:
                raise AudioLoadError(
                    AudioQualityIssue.FILE_EMPTY,
                    "Audio byte buffer is empty (0 bytes)."
                )
            if size > self.thresholds.max_file_size_bytes:
                raise AudioLoadError(
                    AudioQualityIssue.EXCESSIVE_DURATION,
                    f"Audio byte stream exceeds maximum allowed size ({size} bytes)."
                )

            try:
                data, sr = sf.read(bio, dtype="float32", always_2d=False)
            except Exception as err:
                raise AudioLoadError(
                    AudioQualityIssue.FILE_CORRUPTED,
                    f"Failed to decode audio byte buffer: {str(err)}"
                ) from err

            return self._sanitize_array(data, sr)

        raise AudioLoadError(
            AudioQualityIssue.UNSUPPORTED_FORMAT,
            f"Unsupported audio input type: {type(audio_input)}"
        )

    def _sanitize_array(self, data: np.ndarray, sample_rate: int) -> Tuple[np.ndarray, int, int, float]:
        """
        Validates finite values, sample rate limits, and channels.
        Calculates raw multi-channel digital clipping ratio BEFORE any downmix averaging.
        
        Returns:
            Tuple of:
            - mono_samples: np.ndarray (float32)
            - sample_rate: int
            - original_channels: int
            - pre_downmix_clipping_percentage: float (0.0 - 100.0)
        """
        if sample_rate < self.thresholds.min_sample_rate or sample_rate > self.thresholds.max_sample_rate:
            raise AudioLoadError(
                AudioQualityIssue.INVALID_SAMPLE_RATE,
                f"Sample rate {sample_rate} Hz is outside acceptable range ({self.thresholds.min_sample_rate}-{self.thresholds.max_sample_rate} Hz)."
            )

        # Check for non-finite values (NaN / Inf)
        if not np.isfinite(data).all():
            raise AudioLoadError(
                AudioQualityIssue.NON_FINITE_SAMPLES,
                "Audio contains non-finite samples (NaN or Inf)."
            )

        # Measure clipping directly on raw channels before downmixing!
        # When two channels are averaged, one clipped channel (+1.0) and one unclipped channel (e.g. 0.8)
        # would yield 0.9, falsely hiding the digital clipping artifact.
        abs_data = np.abs(data)
        total_raw_elements = data.size
        clipped_raw_elements = int(np.sum(abs_data >= 0.999))
        pre_downmix_clipping_percentage = (float(clipped_raw_elements) / float(total_raw_elements)) * 100.0 if total_raw_elements > 0 else 0.0

        # Opposite-phase stereo channel cancellation defense:
        # If stereo channels are exactly out of phase (e.g. Left = -Right), simple arithmetic mean
        # cancels out all signal to flat silence. Detect this condition before downmix!
        original_channels = 1
        if data.ndim == 2:
            original_channels = data.shape[1]
            if original_channels == 0:
                raise AudioLoadError(AudioQualityIssue.FILE_EMPTY, "Audio has 0 channels.")
            
            if original_channels == 2:
                left = data[:, 0]
                right = data[:, 1]
                # Check for anti-phase cancellation: corr ~= -1.0 with non-zero energy
                norm_l = np.linalg.norm(left)
                norm_r = np.linalg.norm(right)
                if norm_l > 1e-4 and norm_r > 1e-4:
                    dot_prod = np.dot(left, right) / (norm_l * norm_r)
                    if dot_prod < -0.98:
                        # Direct average would cancel out completely! Use Left channel for mono analysis
                        mono_data = left
                    else:
                        mono_data = np.mean(data, axis=1)
                else:
                    mono_data = np.mean(data, axis=1)
            else:
                mono_data = np.mean(data, axis=1)
        elif data.ndim == 1:
            mono_data = data
        else:
            raise AudioLoadError(
                AudioQualityIssue.UNSUPPORTED_FORMAT,
                f"Unsupported array dimension: {data.ndim}D (expected 1D mono or 2D multi-channel)."
            )

        if mono_data.size == 0:
            raise AudioLoadError(AudioQualityIssue.FILE_EMPTY, "Audio contains 0 samples.")

        return mono_data.astype(np.float32, copy=False), sample_rate, original_channels, pre_downmix_clipping_percentage
