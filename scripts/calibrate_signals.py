"""Calibrate the synthetic speech-like signal against SpeechSufficiencyAgent thresholds."""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.agentic.speech_sufficiency import SpeechSufficiencyAgent
from src.agentic.acoustic_intelligence import AcousticIntelligenceAgent


def gen_speech_like(duration_s, sr=16000, seed=0, scale=0.35, duty=0.75):
    rng = np.random.RandomState(seed)
    t = np.arange(int(sr * duration_s)) / sr
    f0 = rng.uniform(120, 260)
    sig = sum(np.sin(2 * np.pi * f0 * h * t + rng.uniform(0, 2 * np.pi)) / h for h in range(1, 8))
    sig += 0.1 * rng.randn(len(t))
    env = ((t % 1.0) < duty).astype(np.float32)
    return (scale * sig * env).astype(np.float32)


for dur in (2.0, 2.5, 3.5):
    speech = gen_speech_like(dur, seed=1)
    r = SpeechSufficiencyAgent().analyze(f"cal_{dur}", speech, 16000)
    r2 = AcousticIntelligenceAgent().analyze(f"cal2_{dur}", speech, 16000)
    print(
        f"dur={dur}s  VAD_speech={r.measurements['usable_speech_duration_seconds']:.2f}s  "
        f"status={r.status.value}/{r2.status.value}  A2={r2.findings['audio_quality_status']} "
        f"high_noise={r2.findings['high_noise_detected']}"
    )
