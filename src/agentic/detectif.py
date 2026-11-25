"""
src/agentic/detectif.py — Detectif.ai evidence adapter (Phase 3).

Only real, configured API calls are made. If Detectif.ai is not configured or
the call fails, evidence is marked UNAVAILABLE/INVALID — never fabricated and
never treated as successful verification.

Configuration (environment only):
- DETECTIF_API_URL   Full analysis endpoint (POST multipart field "file")
- DETECTIF_API_KEY   Bearer token
- DETECTIF_TIMEOUT_SECONDS (default 10)

The response mapping is intentionally tolerant because provider payloads vary;
unrecognised payloads fail closed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

from src.schemas import (
    EvidenceStatus,
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
)


def _unit(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number < 0.0 or number > 1.0:  # NaN / out of range
        return None
    return number


def _first(payload: Dict[str, Any], keys) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


@dataclass(frozen=True)
class DetectifConfig:
    api_url: str = ""
    api_key: str = ""
    timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> "DetectifConfig":
        return cls(
            api_url=os.environ.get("DETECTIF_API_URL", "").strip(),
            api_key=os.environ.get("DETECTIF_API_KEY", "").strip(),
            timeout_seconds=float(os.environ.get("DETECTIF_TIMEOUT_SECONDS", "10")),
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_url and self.api_key)


def normalize_detectif_payload(
    payload: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    """Map a real Detectif.ai response into normalized Aletheia/Eidos evidence."""
    if not isinstance(payload, dict):
        return {"status": "INVALID", "error": "DETECTIF_PAYLOAD_NOT_OBJECT"}

    nested_aletheia = payload.get("aletheia") if isinstance(payload.get("aletheia"), dict) else {}
    nested_eidos = payload.get("eidos") if isinstance(payload.get("eidos"), dict) else {}

    liveness = _unit(_first(nested_aletheia, ("liveness_score", "authenticity_score", "real_score")))
    confidence = _unit(_first(nested_aletheia, ("confidence", "score_confidence")))
    if liveness is None:
        liveness = _unit(_first(payload, ("liveness_score", "authenticity_score", "real_score")))
    if confidence is None:
        confidence = _unit(_first(payload, ("confidence", "score_confidence")))

    deepfake_probability = _unit(
        _first(nested_aletheia, ("deepfake_probability", "fake_probability", "spoof_score"))
    ) or _unit(_first(payload, ("deepfake_probability", "fake_probability", "spoof_score")))
    if liveness is None and deepfake_probability is not None:
        liveness = 1.0 - deepfake_probability
    if confidence is None:
        confidence = _unit(_first(payload, ("confidence",))) or 0.0

    match_score = _unit(
        _first(nested_eidos, ("match_score", "speaker_similarity", "similarity"))
    ) or _unit(_first(payload, ("match_score", "speaker_similarity", "similarity")))
    match_confidence = _unit(
        _first(nested_eidos, ("confidence",))
    ) or _unit(_first(payload, ("identity_confidence",))) or confidence

    provider_status = str(payload.get("status") or nested_aletheia.get("status") or "OK").upper()
    failed = provider_status in {"ERROR", "FAILED", "UNAVAILABLE", "INVALID"}

    if failed:
        aletheia = NormalizedAletheiaEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=session_id)
        eidos = NormalizedEidosEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=session_id)
        return {
            "status": "UNAVAILABLE",
            "provider": "detectif.ai",
            "aletheia": aletheia,
            "eidos": eidos,
            "error": str(payload.get("error") or provider_status)[:300],
            "raw_status": provider_status,
        }

    if liveness is None:
        aletheia = NormalizedAletheiaEvidence(
            status=EvidenceStatus.INVALID,
            session_id=session_id,
            validation_errors=["Detectif.ai response did not contain a usable liveness score."],
        )
    else:
        aletheia = NormalizedAletheiaEvidence(
            liveness_score=liveness,
            confidence=confidence,
            session_id=session_id,
            provider_raw_status=provider_status,
        )

    if match_score is None:
        eidos = NormalizedEidosEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=session_id)
    else:
        eidos = NormalizedEidosEvidence(
            match_score=match_score,
            confidence=match_confidence,
            session_id=session_id,
            provider_raw_status=provider_status,
        )

    return {
        "status": "OK",
        "provider": "detectif.ai",
        "aletheia": aletheia,
        "eidos": eidos,
        "error": None,
        "raw_status": provider_status,
    }


class DetectifClient:
    """Real Detectif.ai HTTP client; no synthetic fallbacks."""

    def __init__(self, config: Optional[DetectifConfig] = None, transport=None):
        self.config = config or DetectifConfig.from_env()
        self._transport = transport

    @property
    def available(self) -> bool:
        return self.config.configured

    def analyze(self, session_id: str, audio_path: str) -> Dict[str, Any]:
        if not self.available:
            return {
                "status": "NOT_CONFIGURED",
                "provider": "detectif.ai",
                "aletheia": NormalizedAletheiaEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=session_id),
                "eidos": NormalizedEidosEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=session_id),
                "error": "DETECTIF_NOT_CONFIGURED",
            }
        if not audio_path or not os.path.exists(audio_path):
            return {
                "status": "UNAVAILABLE",
                "provider": "detectif.ai",
                "aletheia": NormalizedAletheiaEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=session_id),
                "eidos": NormalizedEidosEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=session_id),
                "error": "AUDIO_NOT_FOUND",
            }

        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        try:
            if self._transport is not None:
                payload = self._transport(self.config.api_url, headers, audio_path, self.config.timeout_seconds)
            else:
                if httpx is None:
                    raise RuntimeError("httpx unavailable")
                with open(audio_path, "rb") as handle:
                    files = {"file": (os.path.basename(audio_path), handle, "application/octet-stream")}
                    with httpx.Client(timeout=self.config.timeout_seconds) as client:
                        response = client.post(self.config.api_url, headers=headers, files=files)
                        response.raise_for_status()
                        payload = response.json()
            normalized = normalize_detectif_payload(payload, session_id)
            normalized["provider"] = "detectif.ai"
            return normalized
        except Exception as exc:  # noqa: BLE001 - provider failure is data, not an exception
            return {
                "status": "UNAVAILABLE",
                "provider": "detectif.ai",
                "aletheia": NormalizedAletheiaEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=session_id),
                "eidos": NormalizedEidosEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=session_id),
                "error": f"DETECTIF_REQUEST_FAILED:{type(exc).__name__}",
            }
