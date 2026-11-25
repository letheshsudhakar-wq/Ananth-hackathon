"""
src/agentic/schemas.py — Standardized Agent Data Contracts for Phase 2.

Defines the shared communication schema across all 5 specialized agents:
- Speech Sufficiency Agent
- Acoustic Intelligence Agent
- Network Resilience Agent
- Regional Language Agent
- Cross-Language Identity Agent

Strict invariants:
- Standardized statuses: PASS, WARNING, INCONCLUSIVE, ERROR, NOT_APPLICABLE.
- Structured response guaranteed even on process failure.
- Never treat missing evidence as successful verification.
- Biometric audio is never sent to external LLMs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Any, Dict, List, Optional, Union


def _jsonable(value: Any) -> Any:
    """Recursively convert numpy/scalar values to JSON-native Python types."""
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, bool):
            return bool(value)
        if isinstance(value, int) and not isinstance(value, bool):
            return int(value)
        if isinstance(value, float):
            f = float(value)
            return None if (math.isnan(f) or math.isinf(f)) else f
        return value
    if hasattr(value, "item"):
        try:
            return _jsonable(value.item())
        except Exception:
            pass
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


class AgentStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    INCONCLUSIVE = "INCONCLUSIVE"
    ERROR = "ERROR"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RegionalLanguage(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    KANNADA = "kn"
    TELUGU = "te"
    GUJARATI = "gu"
    UNKNOWN = "unknown"


@dataclass
class StandardAgentResponse:
    """Shared canonical agent response schema."""
    agent_name: str
    session_id: str
    status: AgentStatus
    findings: Dict[str, Any]
    measurements: Dict[str, Optional[float]]
    confidence: float
    limitations: List[str]
    recommended_action: str
    processing_time_ms: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize cleanly to JSON-compatible dictionary."""
        measurements: Dict[str, Any] = {}
        for k, v in self.measurements.items():
            v_json = _jsonable(v)
            measurements[k] = None if v_json is None else round(float(v_json), 4)
        return {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "status": self.status.value,
            "findings": _jsonable(self.findings),
            "measurements": measurements,
            "confidence": round(float(self.confidence), 4),
            "limitations": list(self.limitations),
            "recommended_action": self.recommended_action,
            "processing_time_ms": round(float(self.processing_time_ms), 2),
            "error": self.error,
        }
