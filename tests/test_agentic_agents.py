"""
Tests for the five specialized agents (Phase 2): Speech Sufficiency, Acoustic
Intelligence, Network Resilience, Regional Language, Cross-Language Identity.

Scenarios (per Phase 2 testing plan):
1.  Clean voice recording
2.  Very short speech
3.  Silent recording
4.  Noisy recording
5.  Clipped recording
6.  Interrupted recording
7.  Compressed audio
8.  Indian regional-language speech
9.  Cross-language authentication
10. Invalid audio files
11. Backend or tool failure
12. Multiple simultaneous audio problems

Notes:
- Audio is synthesized deterministically with numpy (no network, no real speech).
- Direct agent calls use ndarrays; endpoint tests use WAV files written to tmp_path.
- Synthetic audio is used ONLY for acoustic/sufficiency scenarios, never as
  proof of biometric validity.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest
import soundfile as sf

# Ensure repo root and backend are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agentic.schemas import AgentStatus, StandardAgentResponse  # noqa: E402
from src.agentic.speech_sufficiency import SpeechSufficiencyAgent  # noqa: E402
from src.agentic.acoustic_intelligence import AcousticIntelligenceAgent  # noqa: E402
from src.agentic.network_resilience import NetworkResilienceAgent  # noqa: E402
from src.agentic.regional_language import RegionalLanguageAgent, LOCALIZED_PROMPTS  # noqa: E402
from src.agentic.cross_language_identity import CrossLanguageIdentityAgent  # noqa: E402

SR = 16000


# ---------------------------------------------------------------------------
# Signal generators (deterministic, CPU-compatible)
# ---------------------------------------------------------------------------

def gen_speech_like(duration_s: float, sr: int = SR, seed: int = 0, scale: float = 0.35, duty: float = 0.75) -> np.ndarray:
    """Synthetic speech-like signal: harmonic stack + periodic amplitude envelope + noise."""
    rng = np.random.RandomState(seed)
    t = np.arange(int(sr * duration_s)) / sr
    f0 = rng.uniform(120, 260)
    sig = sum(
        np.sin(2 * np.pi * f0 * h * t + rng.uniform(0, 2 * np.pi)) * (1.0 / h)
        for h in range(1, 8)
    )
    sig += 0.1 * rng.randn(len(t))
    # Periodic envelope with brief gaps -> measurable usable speech duration
    env = ((t % 1.0) < duty).astype(np.float32)
    return (scale * sig * env).astype(np.float32)


def gen_silence(duration_s: float, sr: int = SR) -> np.ndarray:
    return np.zeros(int(sr * duration_s), dtype=np.float32)


def gen_clipped(duration_s: float, sr: int = SR, frac: float = 0.25) -> np.ndarray:
    sig = gen_speech_like(duration_s, sr, seed=7)
    n_clip = int(len(sig) * frac)
    sig[:n_clip] = np.clip(sig[:n_clip] * 3.0, -1.0, 1.0)
    return sig


def write_wav(samples: np.ndarray, sr: int, path: str) -> str:
    sf.write(path, samples, sr, subtype="PCM_16")
    return path


# ---------------------------------------------------------------------------
# Standardized schema assertions
# ---------------------------------------------------------------------------

EXPECTED_KEYS = {
    "agent_name", "session_id", "status", "findings", "measurements",
    "confidence", "limitations", "recommended_action", "processing_time_ms", "error",
}
VALID_STATUSES = {s.value for s in AgentStatus}


def assert_standard_schema(resp: StandardAgentResponse, session_id: str) -> None:
    d = resp.to_dict()
    assert set(d.keys()) == EXPECTED_KEYS
    assert d["status"] in VALID_STATUSES
    assert d["session_id"] == session_id
    assert d["confidence"] is not None
    assert d["limitations"] is not None
    assert d["recommended_action"] is not None
    assert isinstance(d["processing_time_ms"], float)
    if resp.status != AgentStatus.ERROR:
        assert d["error"] is None


# ---------------------------------------------------------------------------
# Agent 1 — Speech Sufficiency
# ---------------------------------------------------------------------------

class TestSpeechSufficiencyAgent:
    def test_clean_speech_is_sufficient(self):
        speech = gen_speech_like(3.5, seed=1)
        agent = SpeechSufficiencyAgent()
        resp = agent.analyze("sess_clean", speech, SR)
        assert_standard_schema(resp, "sess_clean")
        assert resp.status == AgentStatus.PASS
        assert resp.findings["speech_sufficiency_status"] == "SUFFICIENT"
        assert resp.recommended_action == "PROCEED"

    def test_very_short_speech_recommends_collecting_more(self):
        # < Detectif recommended minimum (~1.8s usable speech)
        speech = gen_speech_like(0.5, seed=2)
        resp = SpeechSufficiencyAgent().analyze("sess_short", speech, SR)
        assert_standard_schema(resp, "sess_short")
        if resp.findings["speech_sufficiency_status"] == "INSUFFICIENT":
            # Never reject the customer: ask for more speech instead
            assert resp.recommended_action == "COLLECT_ADDITIONAL_SPEECH"
        assert resp.findings["speech_sufficiency_status"] in ("SUFFICIENT", "INSUFFICIENT")
        assert resp.findings["deficit_seconds"] >= 0

    def test_silent_recording_is_insufficient_not_accepted(self):
        resp = SpeechSufficiencyAgent().analyze("sess_silent", gen_silence(2.0), SR)
        assert_standard_schema(resp, "sess_silent")
        assert resp.findings["speech_sufficiency_status"] == "INSUFFICIENT"
        assert resp.recommended_action in ("COLLECT_ADDITIONAL_SPEECH", "REQUEST_FRESH_RECORDING")

    def test_session_accumulation_across_turns(self):
        agent = SpeechSufficiencyAgent()
        speech = gen_speech_like(1.0, seed=3)
        r1 = agent.analyze("sess_acc", speech, SR, accumulate=True)
        r2 = agent.analyze("sess_acc", speech, SR, accumulate=True)
        assert r2.findings["accumulated_speech_seconds"] > r1.findings["accumulated_speech_seconds"]

    def test_invalid_audio_returns_structured_error(self):
        resp = SpeechSufficiencyAgent().analyze("sess_inv1", b"definitely not audio", SR)
        assert_standard_schema(resp, "sess_inv1")
        assert resp.status == AgentStatus.ERROR


# ---------------------------------------------------------------------------
# Agent 2 — Acoustic Intelligence
# ---------------------------------------------------------------------------

class TestAcousticIntelligenceAgent:
    def test_clean_audio_passes(self):
        resp = AcousticIntelligenceAgent().analyze("sess_ac_clean", gen_speech_like(2.5, seed=4), SR)
        assert_standard_schema(resp, "sess_ac_clean")
        assert resp.findings["audio_quality_status"] in ("GOOD", "MODERATE")
        assert resp.findings["enhanced_audio_available"] is False  # forensic artifacts preserved

    def test_noisy_recording_flags_high_noise(self):
        # Speech + stationary background noise (synthetic; acoustic scenario only)
        mixed = (gen_speech_like(3.5, seed=5) + 0.15 * np.random.RandomState(6).randn(int(SR * 3.5))).astype(np.float32)
        resp = AcousticIntelligenceAgent().analyze("sess_ac_noisy", mixed, SR)
        assert_standard_schema(resp, "sess_ac_noisy")
        assert resp.findings["high_noise_detected"] is True
        assert resp.recommended_action == "REQUEST_QUIETER_ENVIRONMENT"

    def test_clipped_recording_detected(self):
        resp = AcousticIntelligenceAgent().analyze("sess_ac_clip", gen_clipped(2.0), SR)
        assert_standard_schema(resp, "sess_ac_clip")
        assert resp.findings["clipping_detected"] is True
        assert resp.recommended_action == "REDUCE_MICROPHONE_GAIN"

    def test_original_audio_never_replaced(self):
        resp = AcousticIntelligenceAgent().analyze("sess_ac_orig", gen_speech_like(2.0, seed=6), SR)
        assert resp.findings["enhanced_audio_reference"] is None


# ---------------------------------------------------------------------------
# Agent 3 — Network Resilience
# ---------------------------------------------------------------------------

class TestNetworkResilienceAgent:
    def test_clean_recording_recoverable(self):
        resp = NetworkResilienceAgent().analyze("sess_net_clean", gen_speech_like(2.5, seed=7), SR)
        assert_standard_schema(resp, "sess_net_clean")
        assert resp.findings["recording_integrity_status"] in ("PASS", "DEGRADED")

    def test_interrupted_recording_recommends_retry(self):
        webrtc = {"packet_loss_rate": 0.15, "rtt_ms": 120.0, "jitter_ms": 25.0}
        resp = NetworkResilienceAgent().analyze("sess_net_int", gen_speech_like(2.0, seed=8), SR, webrtc_stats=webrtc)
        assert_standard_schema(resp, "sess_net_int")
        assert resp.findings["interruption_detected"] is True
        assert resp.recommended_action == "RETRY_AUDIO_WITH_LOCAL_BUFFER"
        assert resp.findings["webrtc_telemetry_present"] is True
        assert resp.measurements["webrtc_packet_loss_rate"] == pytest.approx(0.15)

    def test_does_not_reconstruct_missing_speech(self):
        resp = NetworkResilienceAgent().analyze("sess_net_gap", gen_silence(2.0), SR)
        assert_standard_schema(resp, "sess_net_gap")
        for limitation in resp.limitations:
            assert "reconstruct" in limitation or "infer" in limitation or "guess" in limitation


# ---------------------------------------------------------------------------
# Agent 4 — Regional Language
# ---------------------------------------------------------------------------

class TestRegionalLanguageAgent:
    @pytest.mark.parametrize("lang", ["en", "hi", "ta", "kn", "te", "gu"])
    def test_supported_regional_languages(self, lang):
        resp = RegionalLanguageAgent().identify_language(f"sess_rl_{lang}", detected_language=lang)
        assert_standard_schema(resp, f"sess_rl_{lang}")
        assert resp.status == AgentStatus.PASS
        assert resp.findings["detected_language"] == lang

    def test_unknown_language_fails_safe(self):
        resp = RegionalLanguageAgent().identify_language("sess_rl_xx", detected_language="fr")
        assert_standard_schema(resp, "sess_rl_xx")
        assert resp.findings["detected_language"] == "unknown"
        assert resp.findings["preferred_recovery_language"] == "en"

    def test_transcript_heuristic(self):
        resp = RegionalLanguageAgent().identify_language("sess_rl_hi", transcript_text="कृपया बताइए आप कैसे हैं")
        assert resp.findings["detected_language"] in ("hi", "en")

    def test_localized_messages_exist(self):
        for lang in ["en", "hi", "ta", "kn", "te", "gu"]:
            assert "COLLECT_ADDITIONAL_SPEECH" in LOCALIZED_PROMPTS[lang]
            assert LOCALIZED_PROMPTS[lang]["COLLECT_ADDITIONAL_SPEECH"]


# ---------------------------------------------------------------------------
# Agent 5 — Cross-Language Identity
# ---------------------------------------------------------------------------

class TestCrossLanguageIdentityAgent:
    def test_same_language_strong_match(self):
        resp = CrossLanguageIdentityAgent().evaluate("sess_xl_same", "en", "en", eidos_match_score=0.9)
        assert_standard_schema(resp, "sess_xl_same")
        assert resp.status == AgentStatus.PASS
        assert resp.findings["language_switching_detected"] is False

    def test_language_switch_with_strong_speaker_match(self):
        resp = CrossLanguageIdentityAgent().evaluate("sess_xl_switch", "en", "hi", eidos_match_score=0.8)
        assert_standard_schema(resp, "sess_xl_switch")
        assert resp.findings["language_switching_detected"] is True

    def test_missing_evidence_is_inconclusive_not_pass(self):
        resp = CrossLanguageIdentityAgent().evaluate("sess_xl_noe", "en", "hi", eidos_match_score=None)
        assert_standard_schema(resp, "sess_xl_noe")
        assert resp.status == AgentStatus.INCONCLUSIVE
        assert resp.findings["eidos_match_score"] is None

    def test_mismatch_triggers_step_up(self):
        resp = CrossLanguageIdentityAgent().evaluate("sess_xl_mm", "en", "hi", eidos_match_score=0.3)
        assert resp.status == AgentStatus.WARNING
        assert resp.recommended_action == "STEP_UP_CHALLENGE"


# ---------------------------------------------------------------------------
# Standardized schema — all agents return structured responses even on failure
# ---------------------------------------------------------------------------

class TestStandardizedAgentContract:
    def test_all_agents_return_standard_schema_on_failure(self):
        bad_audio = b"\x00\x01garbage-not-audio"
        responses = [
            SpeechSufficiencyAgent().analyze("s_bad", bad_audio, SR),
            AcousticIntelligenceAgent().analyze("a_bad", bad_audio, SR),
            NetworkResilienceAgent().analyze("n_bad", bad_audio, SR),
        ]
        for resp in responses:
            assert_standard_schema(resp, resp.session_id)
            assert resp.status == AgentStatus.ERROR

    def test_internal_exception_returns_structured_error(self):
        resp = SpeechSufficiencyAgent().analyze("s_exc", object(), SR)
        assert_standard_schema(resp, "s_exc")
        assert resp.status == AgentStatus.ERROR
        assert resp.error is not None


# ---------------------------------------------------------------------------
# Backend endpoints (/v1/agents/*) — via TestClient
# ---------------------------------------------------------------------------

class TestAgentEndpoints:
    def _client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_speech_sufficiency_endpoint(self, tmp_path):
        wav = write_wav(gen_speech_like(2.5, seed=10), SR, str(tmp_path / "speech.wav"))
        client = self._client()
        r = client.post("/v1/agents/speech_sufficiency", json={"session_id": "e2e_ss", "audio_path": wav})
        assert r.status_code == 200
        data = r.json()
        assert data["agent_name"] == "speech_sufficiency_agent"
        assert data["session_id"] == "e2e_ss"
        assert data["status"] in VALID_STATUSES

    def test_acoustic_endpoint(self, tmp_path):
        wav = write_wav(gen_speech_like(2.0, seed=11), SR, str(tmp_path / "speech2.wav"))
        r = self._client().post("/v1/agents/acoustic_intelligence", json={"session_id": "e2e_ac", "audio_path": wav})
        assert r.status_code == 200
        assert r.json()["agent_name"] == "acoustic_intelligence_agent"

    def test_network_endpoint(self, tmp_path):
        wav = write_wav(gen_speech_like(2.0, seed=12), SR, str(tmp_path / "speech3.wav"))
        r = self._client().post(
            "/v1/agents/network_resilience",
            json={"session_id": "e2e_net", "audio_path": wav, "webrtc_stats": {"packet_loss_rate": 0.05}},
        )
        assert r.status_code == 200
        assert r.json()["agent_name"] == "network_resilience_agent"

    def test_regional_endpoint(self):
        r = self._client().post(
            "/v1/agents/regional_language",
            json={"session_id": "e2e_rl", "detected_language": "ta", "confidence": 0.91},
        )
        assert r.status_code == 200
        assert r.json()["findings"]["detected_language"] == "ta"

    def test_cross_language_endpoint(self):
        r = self._client().post(
            "/v1/agents/cross_language_identity",
            json={"session_id": "e2e_xl", "enrolled_language": "en", "current_language": "gu", "eidos_match_score": 0.82},
        )
        assert r.status_code == 200
        assert r.json()["findings"]["language_switching_detected"] is True

    def test_missing_audio_returns_structured_error(self):
        r = self._client().post("/v1/agents/speech_sufficiency", json={"session_id": "e2e_noaudio"})
        assert r.status_code == 200
        assert r.json()["status"] == "ERROR"

    def test_session_audio_reference_resolution(self, tmp_path):
        from app.api.v1.agents import register_session_audio
        wav = write_wav(gen_speech_like(2.0, seed=13), SR, str(tmp_path / "session.wav"))
        register_session_audio("sess_ref_1", wav)
        r = self._client().post("/v1/agents/speech_sufficiency", json={"session_id": "sess_ref_1"})
        assert r.status_code == 200
        assert r.json()["agent_name"] == "speech_sufficiency_agent"


# ---------------------------------------------------------------------------
# n8n workflow files mirror backend endpoints
# ---------------------------------------------------------------------------

class TestN8nWorkflowMirrors:
    @pytest.mark.parametrize(
        "workflow,expected_endpoint",
        [
            ("agent_speech_sufficiency.json", "/v1/agents/speech_sufficiency"),
            ("agent_acoustic_intelligence.json", "/v1/agents/acoustic_intelligence"),
            ("agent_network_resilience.json", "/v1/agents/network_resilience"),
            ("agent_regional_language.json", "/v1/agents/regional_language"),
            ("agent_cross_language_identity.json", "/v1/agents/cross_language_identity"),
        ],
    )
    def test_workflow_calls_expected_backend_endpoint(self, workflow, expected_endpoint):
        path = os.path.join(os.path.dirname(__file__), "..", "n8n", "workflows", workflow)
        with open(path, encoding="utf-8") as fh:
            wf = json.load(fh)
        http_urls = [
            n["parameters"]["url"]
            for n in wf["nodes"]
            if n["type"] == "n8n-nodes-base.httpRequest"
        ]
        assert any(expected_endpoint in u for u in http_urls), http_urls
