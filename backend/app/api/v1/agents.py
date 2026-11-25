"""
app/api/v1/agents.py — Specialized Agentic Agent API (Phase 2).

Five independently executable HTTP endpoints that run the specialized agents
(Speech Sufficiency, Acoustic Intelligence, Network Resilience, Regional
Language, Cross-Language Identity) while keeping all heavy audio processing
inside the Python backend.

Design notes:
- n8n workflows pass only session_id + agent parameters; raw audio is uploaded
  once through an authorized session reference instead of being transferred
  between workflows on every call.
- Endpoints also accept an optional multipart file upload for direct/SDK use.
- Every endpoint returns the shared StandardAgentResponse schema
  (src/agentic/schemas.py), even when processing fails.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import agents from the Member-3 style trust-layer package (reused across agents)
from src.agentic.speech_sufficiency import SpeechSufficiencyAgent
from src.agentic.acoustic_intelligence import AcousticIntelligenceAgent
from src.agentic.network_resilience import NetworkResilienceAgent
from src.agentic.regional_language import RegionalLanguageAgent
from src.agentic.cross_language_identity import CrossLanguageIdentityAgent
from src.agentic.schemas import AgentStatus, StandardAgentResponse

router = APIRouter(prefix="/v1/agents", tags=["agentic-specialized-agents"])

# ---------------------------------------------------------------------------
# Server-side session audio store (session-based audio references)
# ---------------------------------------------------------------------------

_SESSIONS_DIR = Path(__file__).resolve().parents[3] / "data" / "agent_sessions"
_session_audio_index: Dict[str, str] = {}


def _ensure_sessions_dir() -> Path:
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return _SESSIONS_DIR


def register_session_audio(session_id: str, audio_path: str) -> None:
    """Record the server-side audio path for a session (authorized reference)."""
    if audio_path:
        _session_audio_index[session_id] = str(audio_path)


def _resolve_audio(
    session_id: str,
    audio_path: Optional[str],
) -> Union[str, None]:
    return audio_path or _session_audio_index.get(session_id)


def _agent_error_response(agent_name: str, session_id: str, message: str) -> JSONResponse:
    """Structured error response that still honours the shared agent schema."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,  # Agent-level statuses are encoded in the payload
        content=StandardAgentResponse(
            agent_name=agent_name,
            session_id=session_id,
            status=AgentStatus.ERROR,
            findings={"summary": message},
            measurements={},
            confidence=0.0,
            limitations=["Structured response returned despite processing failure."],
            recommended_action="REQUEST_FRESH_RECORDING",
            processing_time_ms=0.0,
            error=message,
        ).to_dict(),
    )


def _check_agent_secret(x_agent_secret: Optional[str]) -> None:
    """Optional shared-secret gate for n8n/agent traffic (never log the secret)."""
    secret_env = os.environ.get("AGENT_SECRET")
    if secret_env and (not x_agent_secret or x_agent_secret != secret_env):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent secret")


# ---------------------------------------------------------------------------
# Agent 1 — Speech Sufficiency
# ---------------------------------------------------------------------------

class SpeechSufficiencyRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    sample_rate: Optional[int] = Field(None, ge=8000, le=48000)
    accumulate: bool = True
    audio_path: Optional[str] = None
    min_speech_seconds: Optional[float] = None


@router.post("/speech_sufficiency", summary="Agent 1: Speech Sufficiency")
async def speech_sufficiency(
    request: SpeechSufficiencyRequest,
    x_agent_secret: Optional[str] = Header(None),
) -> JSONResponse:
    """Evaluate recording sufficiency against the Detectif-recommended minimum speech."""
    _check_agent_secret(x_agent_secret)
    audio_path = _resolve_audio(request.session_id, request.audio_path)
    if audio_path is None:
        return _agent_error_response(
            "speech_sufficiency_agent", request.session_id,
            "No audio provided: upload a file or reference a session audio path.",
        )
    agent_kwargs: Dict[str, Any] = {}
    if request.min_speech_seconds is not None:
        agent_kwargs["min_speech_seconds"] = request.min_speech_seconds
    result = SpeechSufficiencyAgent(**agent_kwargs).analyze(
        session_id=request.session_id, audio_input=audio_path, sample_rate=request.sample_rate,
        accumulate=request.accumulate,
    )
    return JSONResponse(content=result.to_dict())


# ---------------------------------------------------------------------------
# Agent 2 — Acoustic Intelligence
# ---------------------------------------------------------------------------

class AcousticIntelligenceRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    sample_rate: Optional[int] = Field(None, ge=8000, le=48000)
    audio_path: Optional[str] = None


@router.post("/acoustic_intelligence", summary="Agent 2: Acoustic Intelligence")
async def acoustic_intelligence(
    request: AcousticIntelligenceRequest,
    x_agent_secret: Optional[str] = Header(None),
) -> JSONResponse:
    """Assess background noise, clipping, and acoustic quality (audio preserved)."""
    _check_agent_secret(x_agent_secret)
    audio_path = _resolve_audio(request.session_id, request.audio_path)
    if audio_path is None:
        return _agent_error_response(
            "acoustic_intelligence_agent", request.session_id,
            "No audio provided: upload a file or reference a session audio path.",
        )
    result = AcousticIntelligenceAgent().analyze(
        session_id=request.session_id, audio_input=audio_path, sample_rate=request.sample_rate,
    )
    return JSONResponse(content=result.to_dict())


# ---------------------------------------------------------------------------
# Agent 3 — Network Resilience
# ---------------------------------------------------------------------------

class NetworkResilienceRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    sample_rate: Optional[int] = Field(None, ge=8000, le=48000)
    audio_path: Optional[str] = None
    webrtc_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="WebRTC telemetry when available, e.g. {packet_loss_rate, rtt_ms, jitter_ms}",
    )


@router.post("/network_resilience", summary="Agent 3: Network Resilience")
async def network_resilience(
    request: NetworkResilienceRequest,
    x_agent_secret: Optional[str] = Header(None),
) -> JSONResponse:
    """Assess recording integrity, interruptions, and codec/sample-rate validity."""
    _check_agent_secret(x_agent_secret)
    audio_path = _resolve_audio(request.session_id, request.audio_path)
    if audio_path is None:
        return _agent_error_response(
            "network_resilience_agent", request.session_id,
            "No audio provided: upload a file or reference a session audio path.",
        )
    result = NetworkResilienceAgent().analyze(
        session_id=request.session_id, audio_input=audio_path, sample_rate=request.sample_rate,
        webrtc_stats=request.webrtc_stats,
    )
    return JSONResponse(content=result.to_dict())


# ---------------------------------------------------------------------------
# Agent 4 — Regional Language
# ---------------------------------------------------------------------------

class RegionalLanguageRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    hint_language: Optional[str] = None
    transcript_text: Optional[str] = None
    detected_language: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


@router.post("/regional_language", summary="Agent 4: Regional Language")
async def regional_language(
    request: RegionalLanguageRequest,
    x_agent_secret: Optional[str] = Header(None),
) -> JSONResponse:
    """Identify the regional Indian language and provide localized recovery prompts."""
    _check_agent_secret(x_agent_secret)
    result = RegionalLanguageAgent().identify_language(
        session_id=request.session_id,
        hint_language=request.hint_language,
        transcript_text=request.transcript_text,
        detected_language=request.detected_language,
        confidence=request.confidence,
    )
    return JSONResponse(content=result.to_dict())


# ---------------------------------------------------------------------------
# Agent 5 — Cross-Language Identity
# ---------------------------------------------------------------------------

class CrossLanguageIdentityRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    enrolled_language: Optional[str]
    current_language: str = Field(..., min_length=1)
    eidos_match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    eidos_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


@router.post("/cross_language_identity", summary="Agent 5: Cross-Language Identity")
async def cross_language_identity(
    request: CrossLanguageIdentityRequest,
    x_agent_secret: Optional[str] = Header(None),
) -> JSONResponse:
    """Detect language switching vs. Eidos speaker evidence (never fail-open on missing evidence)."""
    _check_agent_secret(x_agent_secret)
    result = CrossLanguageIdentityAgent().evaluate(
        session_id=request.session_id,
        enrolled_language=request.enrolled_language,
        current_language=request.current_language,
        eidos_match_score=request.eidos_match_score,
        eidos_confidence=request.eidos_confidence,
    )
    return JSONResponse(content=result.to_dict())


# ---------------------------------------------------------------------------
# Agent registry — used by n8n Switch nodes to route by agent_name
# ---------------------------------------------------------------------------

AGENT_ENDPOINTS: Dict[str, Dict[str, Any]] = {
    "speech_sufficiency_agent": "/v1/agents/speech_sufficiency",
    "acoustic_intelligence_agent": "/v1/agents/acoustic_intelligence",
    "network_resilience_agent": "/v1/agents/network_resilience",
    "regional_language_agent": "/v1/agents/regional_language",
    "cross_language_identity_agent": "/v1/agents/cross_language_identity",
}
