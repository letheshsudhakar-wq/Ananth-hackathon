"""
Audio Signal Feature Extractor Module.

Uses frame-based NumPy & SciPy signal processing:
- Total duration (s)
- RMS level (dBFS) and Peak amplitude
- Digital clipping percentage
- Frame-based background noise floor estimation (heuristic minimum energy tracking)
- Frame-based heuristic speech duration & silence percentage
- Estimated Signal-to-Noise Ratio (SNR in dB)

Important distinction:
Heuristic frame-energy speech & noise estimations are lightweight approximations
for pre-flight quality gating, NOT certified acoustic VAD or speaker identity checks.
"""

from typing import Dict, Tuple, Optional
import numpy as np


class AudioFeatureExtractor:
    """Lightweight deterministic feature extractor for audio quality evaluation."""

    def __init__(self, frame_ms: float = 25.0, hop_ms: float = 10.0):
        self.frame_ms = frame_ms
        self.hop_ms = hop_ms

    def extract_features(
        self,
        samples: np.ndarray,
        sample_rate: int
    ) -> Dict[str, Optional[float]]:
        """
        Extracts physical acoustic and digital signal features from 1D mono float32 samples.
        """
        num_samples = len(samples)
        duration_seconds = float(num_samples) / float(sample_rate)

        if num_samples == 0:
            return {
                "duration_seconds": 0.0,
                "rms_dbfs": None,
                "peak_amplitude": None,
                "clipping_percentage": None,
                "estimated_noise_level_dbfs": None,
                "estimated_snr_db": None,
                "estimated_speech_duration_seconds": None,
                "silence_percentage": None,
            }

        # 1. Peak Amplitude and Clipping
        # Samples >= 0.999 or <= -0.999 on normalized float are considered digitally clipped
        abs_samples = np.abs(samples)
        peak_amp = float(np.max(abs_samples))
        clipped_count = int(np.sum(abs_samples >= 0.999))
        clipping_pct = (float(clipped_count) / float(num_samples)) * 100.0

        # 2. Global RMS Level in dBFS
        # Reference full-scale sine RMS is 1/sqrt(2) ≈ 0.707, but for digital full-scale peak 1.0,
        # standard digital dBFS defines RMS of full scale square as 0 dBFS or sine as -3 dBFS.
        # Here: 20 * log10(rms + 1e-12)
        rms_raw = float(np.sqrt(np.mean(samples ** 2)))
        rms_dbfs = 20.0 * np.log10(rms_raw + 1e-12)

        # 3. Frame-based Energy Decomposition (Speech, Silence, and Noise Floor)
        frame_len = max(int((self.frame_ms / 1000.0) * sample_rate), 16)
        hop_len = max(int((self.hop_ms / 1000.0) * sample_rate), 8)

        if num_samples < frame_len:
            # Signal too short for full framing; return basic estimates
            noise_floor_dbfs = rms_dbfs
            snr_db = 0.0
            speech_sec = duration_seconds if rms_dbfs > -45.0 else 0.0
            silence_pct = 0.0 if speech_sec > 0 else 100.0
        else:
            # Vectorized frame slicing
            num_frames = 1 + (num_samples - frame_len) // hop_len
            shape = (num_frames, frame_len)
            strides = (samples.strides[0] * hop_len, samples.strides[0])
            frames = np.lib.stride_tricks.as_strided(samples, shape=shape, strides=strides)

            # Frame energy (RMS per frame in dBFS)
            frame_rms = np.sqrt(np.mean(frames ** 2, axis=1))
            frame_dbfs = 20.0 * np.log10(frame_rms + 1e-12)

            # Heuristic Noise Floor Estimation:
            # The bottom 10th-15th percentile of frame energies is a robust, lightweight estimator
            # for ambient stationary background noise in interactive speech recordings.
            # Absolute silence threshold: below -80 dBFS (e.g. true zero array)
            if rms_dbfs < -80.0:
                noise_floor_dbfs = -90.0
                speech_sec = 0.0
                silence_pct = 100.0
                snr_db = 0.0
            else:
                noise_floor_dbfs = float(np.percentile(frame_dbfs, 12))

                # Speech vs Silence Detection:
                # Active speech frames are defined as frames with energy significantly above the noise floor
                # (at least 9 dB above noise) AND above absolute minimal audible threshold (-50 dBFS).
                speech_threshold_db = max(noise_floor_dbfs + 9.0, -50.0)
                speech_frames_mask = frame_dbfs >= speech_threshold_db

                speech_frame_count = int(np.sum(speech_frames_mask))
                total_frames = len(frame_dbfs)

                # Convert frame counts back to estimated time
                estimated_speech_ratio = float(speech_frame_count) / float(total_frames)
                speech_sec = duration_seconds * estimated_speech_ratio
                silence_pct = (1.0 - estimated_speech_ratio) * 100.0

                # Estimated SNR calculation:
                # SNR = RMS of active speech frames - Estimated noise floor
                if speech_frame_count > 0:
                    active_speech_dbfs = float(np.percentile(frame_dbfs[speech_frames_mask], 75))
                    snr_db = max(active_speech_dbfs - noise_floor_dbfs, 0.0)
                else:
                    # When no speech frames detected:
                    # If recording has low energy or is silent, SNR is not defined as noisy background; it is 0.0
                    snr_db = 0.0

        return {
            "duration_seconds": duration_seconds,
            "rms_dbfs": rms_dbfs,
            "peak_amplitude": peak_amp,
            "clipping_percentage": clipping_pct,
            "estimated_noise_level_dbfs": noise_floor_dbfs,
            "estimated_snr_db": snr_db,
            "estimated_speech_duration_seconds": speech_sec,
            "silence_percentage": silence_pct,
        }
