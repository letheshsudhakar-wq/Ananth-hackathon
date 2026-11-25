"""
src/agentic/gemini_client.py — Shared Gemini Flash client (Phase 3).

Security & reliability contract:
- One shared LLM configured only through environment variables
  (GEMINI_API_KEY, GEMINI_MODEL). Keys are never logged or returned.
- Structured JSON output only, validated by a caller-supplied validator.
- Bounded retries with deterministic fallback (no fabricated content).
- Only redacted, structured findings are sent. Raw audio / biometric
  recordings and transcripts are never transmitted.
- External text is treated as untrusted data, never as instructions.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

try:  # httpx is a backend dependency; keep module importable without it.
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

DEFAULT_MODEL = "gemini-2.5-flash"
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_MAX_PROMPT_CHARS = 6000
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(value: Any, max_chars: int = 500) -> str:
    """Collapse untrusted text to a safe, bounded single-line string."""
    if value is None:
        return ""
    text = str(value)
    text = _CONTROL_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def compact_agent_findings(findings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Reduce agent findings to a compact, redacted structure for the LLM.
    Only status / summary / action / a few numeric measurements are included.
    """
    compact: Dict[str, Any] = {}
    if not isinstance(findings, dict):
        return compact
    for name, payload in list(findings.items())[:6]:
        if not isinstance(payload, dict):
            continue
        inner = payload.get("findings") if isinstance(payload.get("findings"), dict) else {}
        measurements = payload.get("measurements") if isinstance(payload.get("measurements"), dict) else {}
        safe_measurements = {
            str(k)[:40]: v
            for k, v in list(measurements.items())[:5]
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }
        compact[str(name)[:48]] = {
            "status": sanitize_text(payload.get("status"), 32),
            "summary": sanitize_text(inner.get("summary"), 220),
            "recommended_action": sanitize_text(payload.get("recommended_action"), 48),
            "measurements": safe_measurements,
            "error": sanitize_text(payload.get("error"), 160) or None,
        }
    return compact


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str = ""
    model: str = DEFAULT_MODEL
    timeout_seconds: float = 8.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "GeminiConfig":
        return cls(
            api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
            model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            timeout_seconds=float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "8")),
            max_retries=max(0, min(int(os.environ.get("GEMINI_MAX_RETRIES", "2")), 3)),
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class GeminiResult:
    data: Optional[Dict[str, Any]] = None
    used: bool = False
    attempts: int = 0
    error: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    latency_ms: float = 0.0

    @property
    def ok(self) -> bool:
        return self.data is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "used": self.used,
            "attempts": self.attempts,
            "ok": self.ok,
            "error": self.error,
            "errors": list(self.errors),
            "latency_ms": round(self.latency_ms, 2),
        }


def _extract_text(payload: Dict[str, Any]) -> Optional[str]:
    try:
        candidates = payload.get("candidates") or []
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts") or []
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")]
        return "".join(texts).strip() or None
    except Exception:
        return None


def _parse_json_text(text: str) -> Optional[Dict[str, Any]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except Exception:
            return None
    return data if isinstance(data, dict) else None


class GeminiClient:
    """Small, dependency-light Gemini Flash JSON client with deterministic fallback."""

    def __init__(
        self,
        config: Optional[GeminiConfig] = None,
        transport: Optional[Callable[[str, Dict[str, str], Dict[str, Any], float], Dict[str, Any]]] = None,
    ):
        self.config = config or GeminiConfig.from_env()
        self._transport = transport
        self._client = None
        if self._transport is None and httpx is not None:
            self._client = httpx.Client(timeout=self.config.timeout_seconds)

    @property
    def available(self) -> bool:
        return self.config.configured

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _post(self, url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        if self._transport is not None:
            return self._transport(url, headers, payload, timeout)
        if self._client is None:
            raise RuntimeError("Gemini transport unavailable")
        response = self._client.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        validator: Callable[[Dict[str, Any]], bool],
        max_output_tokens: int = 384,
    ) -> GeminiResult:
        """
        Call Gemini Flash once (with bounded retries) and return validated JSON.
        Never raises; failures return data=None so callers can use templates.
        """
        started = time.perf_counter()
        result = GeminiResult()
        if not self.available:
            result.error = "GEMINI_NOT_CONFIGURED"
            result.latency_ms = (time.perf_counter() - started) * 1000.0
            return result

        prompt = sanitize_text(prompt, _MAX_PROMPT_CHARS)
        system_instruction = sanitize_text(system_instruction, 1500)
        url = f"{_BASE_URL}/models/{self.config.model}:generateContent"
        headers = {
            "x-goog-api-key": self.config.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
            },
        }

        for attempt in range(1, self.config.max_retries + 2):
            result.attempts = attempt
            try:
                raw = self._post(url, headers, payload, self.config.timeout_seconds)
                result.used = True
                text = _extract_text(raw)
                if not text:
                    result.errors.append("EMPTY_LLM_RESPONSE")
                    continue
                data = _parse_json_text(text)
                if data is None:
                    result.errors.append("MALFORMED_LLM_JSON")
                    continue
                if not validator(data):
                    result.errors.append("LLM_SCHEMA_VALIDATION_FAILED")
                    continue
                result.data = data
                result.error = None
                result.latency_ms = (time.perf_counter() - started) * 1000.0
                return result
            except Exception as exc:  # noqa: BLE001 - bounded retry boundary
                result.used = True
                # Never surface API keys or raw payloads in errors.
                result.errors.append(f"GEMINI_REQUEST_FAILED:{type(exc).__name__}")
                if attempt <= self.config.max_retries:
                    time.sleep(min(0.25 * attempt, 0.75))
                continue

        result.error = result.errors[-1] if result.errors else "GEMINI_FAILED"
        result.latency_ms = (time.perf_counter() - started) * 1000.0
        return result
