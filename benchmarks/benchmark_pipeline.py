"""
Performance Benchmarking and Latency Profiling Script (Task 6 & 7).

Benchmarks representative audio signals (5s, 10s, 30s) and full pipeline execution:
1. Audio validation & feature extraction (DSP)
2. Adaptive Trust Engine evaluation
3. Recovery engine turn processing & state machine
4. Decision explanation generation

Separates local compute latency from mock/network API latency.
Reports median and p95 latencies over repeated iterations.
"""

import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import numpy as np
from typing import Dict, List, Any
import json

from src.audio_intelligence import analyze_audio
from src.trust_engine.engine import AdaptiveTrustEngine
from src.trust_engine.recovery import AdaptiveRecoveryEngine
from src.trust_engine.explainer import DecisionExplainer
from src.schemas import (
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    ActionRiskLevel,
)


def generate_benchmark_signal(duration: float, sample_rate: int = 16000) -> np.ndarray:
    np.random.seed(42)
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    # Speech tone + gentle noise
    signal = 0.5 * np.sin(2 * np.pi * 350.0 * t) + np.random.normal(0, 0.01, len(t))
    return signal.astype(np.float32)


def benchmark_pipeline(iterations: int = 20) -> Dict[str, Any]:
    durations = [5.0, 10.0, 30.0]
    results = {}

    trust_engine = AdaptiveTrustEngine()
    recovery_engine = AdaptiveRecoveryEngine()

    for dur in durations:
        audio = generate_benchmark_signal(dur)
        sample_rate = 16000

        audio_latencies = []
        trust_latencies = []
        recovery_latencies = []
        e2e_latencies = []

        for i in range(iterations):
            # 1. Audio analysis
            t0 = time.perf_counter()
            audio_report = analyze_audio(audio, sample_rate=sample_rate)
            t1 = time.perf_counter()
            audio_latencies.append((t1 - t0) * 1000.0)

            # Upstream evidence mock
            aletheia = NormalizedAletheiaEvidence(liveness_score=0.92, confidence=0.88, session_id=f"bench_{dur}_{i}")
            eidos = NormalizedEidosEvidence(match_score=0.90, confidence=0.85, session_id=f"bench_{dur}_{i}")

            # 2. Trust Engine
            t2 = time.perf_counter()
            trust_output = trust_engine.evaluate({}, audio_report, aletheia, eidos, ActionRiskLevel.LOW)
            t3 = time.perf_counter()
            trust_latencies.append((t3 - t2) * 1000.0)

            # 3. Recovery Turn
            session = recovery_engine.get_or_create_session(f"bench_{dur}_{i}", "caller_bench")
            t4 = time.perf_counter()
            rec_output = recovery_engine.process_turn(session, audio_report, trust_output, aletheia, eidos)
            _ = DecisionExplainer.explain(trust_output, audio_report, aletheia, eidos, rec_output)
            t5 = time.perf_counter()
            recovery_latencies.append((t5 - t4) * 1000.0)

            # End to end local processing
            e2e_latencies.append((t5 - t0) * 1000.0)

        results[f"{int(dur)}s_audio"] = {
            "audio_dsp_median_ms": round(float(np.median(audio_latencies)), 2),
            "audio_dsp_p95_ms": round(float(np.percentile(audio_latencies, 95)), 2),
            "trust_engine_median_ms": round(float(np.median(trust_latencies)), 3),
            "trust_engine_p95_ms": round(float(np.percentile(trust_latencies, 95)), 3),
            "recovery_explainer_median_ms": round(float(np.median(recovery_latencies)), 3),
            "recovery_explainer_p95_ms": round(float(np.percentile(recovery_latencies, 95)), 3),
            "e2e_local_median_ms": round(float(np.median(e2e_latencies)), 2),
            "e2e_local_p95_ms": round(float(np.percentile(e2e_latencies, 95)), 2),
        }

    return results


if __name__ == "__main__":
    bench = benchmark_pipeline(iterations=25)
    print(json.dumps(bench, indent=2))
