"""
app/api/v1/orchestration.py — n8n Multi-Agent Orchestration & Specialized Agent Endpoints (Phase 2).

Provides additive, backward-compatible integration endpoints for n8n:
- Foundation bridge: /v1/n8n/health, /v1/n8n/bridge  (Phase 1 — unchanged)
- Agent 1: /v1/n8n/agent/speech-sufficiency
- Agent 2: /v1/n8n/agent/acoustic-intelligence
- Agent 3: /v1/n8n/agent/network-resilience
- Agent 4: /v1/n8n/agent/regional-language
- Agent 5: /v1/n8n/agent/cross-language-identity
"""

from __future__ import annotations

import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException, status, Header

from src.pipeline import AnanthPipeline
from src.schemas import (
    NormalizedAletheiaEvidence,
    NormalizedEidosEvidence,
    ActionRiskLevel,
    EvidenceStatus,
    AudioQualityReport,
    AudioQualityStatus,
    RecommendedAction,
)
from src.agentic.speech_sufficiency import SpeechSufficiencyAgent
from src.agentic.acoustic_intelligence import AcousticIntelligenceAgent
from src.agentic.network_resilience import NetworkResilienceAgent
from src.agentic.regional_language import RegionalLanguageAgent
from src.agentic.cross_language_identity import CrossLanguageIdentityAgent

router = APIRouter(prefix="/v1/n8n", tags=["n8n-orchestration"])

_pipeline = AnanthPipeline(production_mode=False)
_agent_speech = SpeechSufficiencyAgent()
_agent_acoustic = AcousticIntelligenceAgent()
_agent_network = NetworkResilienceAgent()
_agent_language = RegionalLanguageAgent()
_agent_cross_lang = CrossLanguageIdentityAgent()


# ==============================================================================
# SCHEMAS
# ==============================================================================

class N8nAgentBridgeRequest(BaseModel):
    session_id: str = Field(..., description="Unique caller authentication session ID")
    caller_id: str = Field(..., description="Unique caller identifier")
    action_risk: str = Field(default="MEDIUM", description="LOW | MEDIUM | HIGH | FINANCIAL")
    agent_name: str = Field(default="orchestrator", description="Calling n8n agent name")
    aletheia_liveness_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    aletheia_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    eidos_match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    eidos_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    raw_audio_provided: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class N8nAgentBridgeResponse(BaseModel):
    status: str
    session_id: str
    caller_id: str
    verification_status: str
    decision: str
    session_state: str
    recovery_action: str
    customer_message: str
    sensitive_operations_paused: bool
    independent_auth_required: bool
    terminal_state: bool
    agent_routed_to: str
    processing_time_ms: float
    reason_codes: list[str]


class SpeechSufficiencyPayload(BaseModel):
    session_id: str
    duration_seconds: Optional[float] = Field(None, ge=0.0)
    estimated_speech_seconds: Optional[float] = Field(None, ge=0.0)
    silence_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    accumulate: bool = Field(default=True)
    audio_file_path: Optional[str] = None


class AcousticIntelligencePayload(BaseModel):
    session_id: str
    snr_db: Optional[float] = None
    noise_dbfs: Optional[float] = None
    rms_dbfs: Optional[float] = None
    clipping_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    audio_file_path: Optional[str] = None


class NetworkResiliencePayload(BaseModel):
    session_id: str
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    webrtc_packet_loss_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    webrtc_jitter_ms: Optional[float] = Field(None, ge=0.0)
    webrtc_rtt_ms: Optional[float] = Field(None, ge=0.0)
    audio_file_path: Optional[str] = None


class RegionalLanguagePayload(BaseModel):
    session_id: str
    hint_language: Optional[str] = "en"
    detected_language: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    transcript_text: Optional[str] = None


class CrossLanguageIdentityPayload(BaseModel):
    session_id: str
    enrolled_language: Optional[str] = None
    current_language: str
    eidos_match_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    eidos_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


# ==============================================================================
# PHASE 1 BRIDGE ENDPOINTS — backward compatible
# ==============================================================================

@router.get("/health", summary="n8n Integration Health Check")
async def n8n_bridge_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "ANANTH n8n Agentic Orchestration Bridge",
        "timestamp": time.time(),
        "ready": True,
        "agents": [
            "speech_sufficiency_agent",
            "acoustic_intelligence_agent",
            "network_resilience_agent",
            "regional_language_agent",
            "cross_language_identity_agent",
        ],
    }


@router.post(
    "/bridge",
    response_model=N8nAgentBridgeResponse,
    summary="n8n Agent Decision & Trust Bridge",
)
async def evaluate_agent_bridge(
    payload: N8nAgentBridgeRequest,
    x_n8n_secret: Optional[str] = Header(None),
) -> N8nAgentBridgeResponse:
    t0 = time.perf_counter()
    try:
        risk_level = ActionRiskLevel(payload.action_risk.upper())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RISK_TIER", "message": f"Invalid action_risk: {payload.action_risk}"},
        )

    aletheia_ev = (
        NormalizedAletheiaEvidence(
            liveness_score=payload.aletheia_liveness_score,
            confidence=payload.aletheia_confidence or 0.85,
            session_id=payload.session_id,
        )
        if payload.aletheia_liveness_score is not None
        else NormalizedAletheiaEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=payload.session_id)
    )

    eidos_ev = (
        NormalizedEidosEvidence(
            match_score=payload.eidos_match_score,
            confidence=payload.eidos_confidence or 0.85,
            session_id=payload.session_id,
        )
        if payload.eidos_match_score is not None
        else NormalizedEidosEvidence(status=EvidenceStatus.UNAVAILABLE, session_id=payload.session_id)
    )

    audio_report = AudioQualityReport(
        valid=True,
        quality_status=AudioQualityStatus.GOOD,
        suitable_for_authentication=True,
        duration_seconds=3.0,
        estimated_speech_duration_seconds=2.5,
        sample_rate=16000,
        channel_count=1,
        estimated_noise_level_dbfs=-55.0,
        estimated_snr_db=25.0,
        silence_percentage=15.0,
        clipping_percentage=0.0,
        rms_dbfs=-20.0,
        peak_amplitude=0.6,
        detected_issues=[],
        recommended_action=RecommendedAction.PROCEED,
    )

    result = _pipeline.stage_b_evaluate_and_recover(
        session_id=payload.session_id,
        caller_id=payload.caller_id,
        audio_report=audio_report,
        aletheia_evidence=aletheia_ev,
        eidos_evidence=eidos_ev,
        action_risk_level=risk_level,
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return N8nAgentBridgeResponse(
        status="success",
        session_id=result["session_id"],
        caller_id=result["caller_id"],
        verification_status=result["verification_status"],
        decision=result["decision"],
        session_state=result["session_state"],
        recovery_action=result["recovery_action"],
        customer_message=result["customer_message"],
        sensitive_operations_paused=result["sensitive_operations_paused"],
        independent_auth_required=result["independent_auth_required"],
        terminal_state=result["terminal_state"],
        agent_routed_to=payload.agent_name,
        processing_time_ms=elapsed_ms,
        reason_codes=result["reason_codes"],
    )


# ==============================================================================
# PHASE 2 SPECIALIZED AGENT ENDPOINTS
# ==============================================================================

@router.post("/agent/speech-sufficiency", summary="Agent 1: Speech Sufficiency Evaluation")
async def evaluate_speech_sufficiency(payload: SpeechSufficiencyPayload) -> Dict[str, Any]:
    import numpy as np
    if payload.audio_file_path:
        resp = _agent_speech.analyze(session_id=payload.session_id, audio_input=payload.audio_file_path, accumulate=payload.accumulate)
        return resp.to_dict()
    sr = 16000
    dur = payload.duration_seconds if payload.duration_seconds is not None else 3.0
    speech_dur = payload.estimated_speech_seconds if payload.estimated_speech_seconds is not None else 2.5
    total_samples = max(int(dur * sr), 100)
    rng = np.random.default_rng(42)
    samples = np.zeros(total_samples, dtype=np.float32) if speech_dur == 0.0 else rng.uniform(-0.3, 0.3, size=total_samples).astype(np.float32)
    resp = _agent_speech.analyze(session_id=payload.session_id, audio_input=samples, sample_rate=sr, accumulate=payload.accumulate)
    return resp.to_dict()


@router.post("/agent/acoustic-intelligence", summary="Agent 2: Acoustic Intelligence Evaluation")
async def evaluate_acoustic_intelligence(payload: AcousticIntelligencePayload) -> Dict[str, Any]:
    import numpy as np
    if payload.audio_file_path:
        resp = _agent_acoustic.analyze(session_id=payload.session_id, audio_input=payload.audio_file_path)
        return resp.to_dict()
    sr = 16000
    rng = np.random.default_rng(42)
    clip_pct = payload.clipping_percentage or 0.0
    samples = rng.uniform(-0.4, 0.4, size=32000).astype(np.float32)
    if clip_pct > 1.0:
        samples[:int(32000 * (clip_pct / 100.0))] = 1.0
    resp = _agent_acoustic.analyze(session_id=payload.session_id, audio_input=samples, sample_rate=sr)
    return resp.to_dict()


@router.post("/agent/network-resilience", summary="Agent 3: Network Resilience Evaluation")
async def evaluate_network_resilience(payload: NetworkResiliencePayload) -> Dict[str, Any]:
    import numpy as np
    sr = payload.sample_rate or 16000
    dur = payload.duration_seconds or 2.5
    rng = np.random.default_rng(42)
    samples = rng.uniform(-0.2, 0.2, size=max(int(dur * sr), 100)).astype(np.float32)
    webrtc_dict = None
    if payload.webrtc_packet_loss_rate is not None:
        webrtc_dict = {"packet_loss_rate": payload.webrtc_packet_loss_rate, "jitter_ms": payload.webrtc_jitter_ms or 0.0, "rtt_ms": payload.webrtc_rtt_ms or 0.0}
    if payload.audio_file_path:
        resp = _agent_network.analyze(session_id=payload.session_id, audio_input=payload.audio_file_path, webrtc_stats=webrtc_dict)
    else:
        resp = _agent_network.analyze(session_id=payload.session_id, audio_input=samples, sample_rate=sr, webrtc_stats=webrtc_dict)
    return resp.to_dict()


@router.post("/agent/regional-language", summary="Agent 4: Regional Language Intelligence")
async def evaluate_regional_language(payload: RegionalLanguagePayload) -> Dict[str, Any]:
    resp = _agent_language.identify_language(session_id=payload.session_id, hint_language=payload.hint_language, detected_language=payload.detected_language, transcript_text=payload.transcript_text, confidence=payload.confidence)
    return resp.to_dict()


@router.post("/agent/cross-language-identity", summary="Agent 5: Cross-Language Identity Evaluation")
async def evaluate_cross_language_identity(payload: CrossLanguageIdentityPayload) -> Dict[str, Any]:
    resp = _agent_cross_lang.evaluate(session_id=payload.session_id, enrolled_language=payload.enrolled_language, current_language=payload.current_language, eidos_match_score=payload.eidos_match_score, eidos_confidence=payload.eidos_confidence)
    return resp.to_dict()


# ==============================================================================
# PHASE 3 — MASTER ORCHESTRATOR, GEMINI RECOVERY & UNIFIED RESPONSE
# Additive endpoints only. Existing Phase 1/2 contracts above are unchanged.
# ==============================================================================

import os as _os
import re as _re
from pathlib import Path as _Path
from fastapi import File as _File, UploadFile as _UploadFile

try:
    from app.api.v1.agents import register_session_audio as _register_session_audio  # FastAPI runtime path
except ImportError:
    from backend.app.api.v1.agents import register_session_audio as _register_session_audio  # test/standalone path
from src.agentic.gemini_client import GeminiConfig as _GeminiConfig
from src.agentic.detectif import DetectifConfig as _DetectifConfig
from src.agentic.orchestrator import (
    OrchestrationRequest as _OrchestrationRequest,
    audio_report_from_dict as _audio_report_from_dict,
    get_orchestrator as _get_orchestrator,
)
from src.agentic.recovery_policy import (
    APPROVED_ACTIONS as _APPROVED_ACTIONS,
    SUPPORTED_LANGUAGES as _SUPPORTED_LANGUAGES,
    build_plan as _build_plan,
    normalize_language as _normalize_language,
)

_PHASE3_SESSION_ID_RE = _re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_PHASE3_AUDIO_EXTENSIONS = {".wav", ".flac", ".ogg", ".mp3", ".m4a", ".webm"}
_PHASE3_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_PHASE3_SESSIONS_DIR = _Path(__file__).resolve().parents[3] / "data" / "agent_sessions"
_PHASE3_REPO_ROOT = _Path(__file__).resolve().parents[4]


class OrchestrationPayload(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    caller_id: str = Field(default="unknown", max_length=128)
    action_risk: str = Field(default="MEDIUM", description="LOW | MEDIUM | HIGH | FINANCIAL")

    @field_validator("action_risk")
    @classmethod
    def validate_action_risk(cls, v: str) -> str:
        normalised = v.upper()
        if normalised not in {"LOW", "MEDIUM", "HIGH", "FINANCIAL"}:
            raise ValueError(f"action_risk must be one of LOW, MEDIUM, HIGH, FINANCIAL; got '{v}'")
        return normalised
    audio_path: Optional[str] = None
    sample_rate: Optional[int] = Field(None, ge=8000, le=48000)
    audio_report: Optional[Dict[str, Any]] = None
    preferred_language: Optional[str] = None
    enrolled_language: Optional[str] = None
    current_language: Optional[str] = None
    transcript_text: Optional[str] = Field(None, max_length=4000)
    language_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    webrtc_stats: Optional[Dict[str, Any]] = None
    aletheia: Optional[Dict[str, Any]] = None
    eidos: Optional[Dict[str, Any]] = None
    detection_result: Optional[Dict[str, Any]] = None
    agent_findings: Optional[Dict[str, Any]] = None
    use_gemini: bool = True
    simulation_mode: bool = False
    agent_timeout_seconds: float = Field(default=12.0, ge=1.0, le=30.0)

    def to_orchestration_request(self) -> _OrchestrationRequest:
        return _OrchestrationRequest(**self.model_dump())


class RecoveryPayload(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    verification_status: Optional[str] = None
    decision: Optional[str] = None
    session_state: Optional[str] = None
    reason_codes: List[str] = Field(default_factory=list)
    recovery_action: Optional[str] = None
    agent_findings: Optional[Dict[str, Any]] = None
    preferred_language: Optional[str] = None
    use_gemini: bool = True


def _check_phase3_secret(x_n8n_secret: Optional[str]) -> None:
    expected = _os.environ.get("N8N_BRIDGE_SECRET")
    if expected and x_n8n_secret != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid n8n bridge secret")


def _safe_phase3_audio_path(audio_path: Optional[str]) -> Optional[str]:
    if not audio_path:
        return None
    candidate = _Path(audio_path).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        raise HTTPException(status_code=400, detail={"code": "AUDIO_NOT_FOUND", "message": "Audio reference not found"})
    allowed_roots = [(_PHASE3_SESSIONS_DIR.parent).resolve(), (_PHASE3_REPO_ROOT / "data").resolve()]
    if not any(resolved == root or root in resolved.parents for root in allowed_roots):
        raise HTTPException(
            status_code=400,
            detail={"code": "AUDIO_PATH_NOT_ALLOWED", "message": "Audio reference must be inside the approved data directory"},
        )
    return str(resolved)


@router.get("/config", summary="Safe orchestration capability status")
async def orchestration_config() -> Dict[str, Any]:
    gemini = _GeminiConfig.from_env()
    detectif = _DetectifConfig.from_env()
    return {
        "status": "ok",
        "gemini": {"configured": gemini.configured, "model": gemini.model if gemini.configured else None},
        "detectif": {"configured": detectif.configured},
        "approved_recovery_actions": list(_APPROVED_ACTIONS),
        "supported_languages": list(_SUPPORTED_LANGUAGES),
        "production_mode": _os.environ.get("ANANTH_PRODUCTION_MODE", "false").lower() == "true",
    }


@router.post("/session/{session_id}/audio", summary="Register session audio (upload once)")
async def upload_session_audio(
    session_id: str,
    file: _UploadFile = _File(...),
    x_n8n_secret: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _check_phase3_secret(x_n8n_secret)
    if not _PHASE3_SESSION_ID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id")
    suffix = _Path(file.filename or "").suffix.lower()
    if suffix not in _PHASE3_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail={"code": "UNSUPPORTED_AUDIO_FORMAT", "message": "Unsupported audio extension"})
    content = await file.read(_PHASE3_MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail={"code": "EMPTY_AUDIO", "message": "Empty upload"})
    if len(content) > _PHASE3_MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail={"code": "AUDIO_TOO_LARGE", "message": "Audio exceeds 25 MB"})
    _PHASE3_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = _PHASE3_SESSIONS_DIR / f"{session_id}{suffix}"
    target.write_bytes(content)  # original bytes preserved; never transformed
    _register_session_audio(session_id, str(target))
    return {"status": "ok", "session_id": session_id, "audio_path": str(target), "size_bytes": len(content)}


@router.post("/prechecks", summary="Audio pre-checks (no audio transfer between n8n nodes)")
async def audio_prechecks(
    payload: OrchestrationPayload,
    x_n8n_secret: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _check_phase3_secret(x_n8n_secret)
    payload.audio_path = _safe_phase3_audio_path(payload.audio_path)
    orchestrator = _get_orchestrator()
    started = time.perf_counter()
    report = orchestrator.precheck(payload.to_orchestration_request())
    report["processing_time_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
    return report


@router.post("/agents/batch", summary="Deterministic routing + concurrent specialized agents")
async def agents_batch(
    payload: OrchestrationPayload,
    x_n8n_secret: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _check_phase3_secret(x_n8n_secret)
    payload.audio_path = _safe_phase3_audio_path(payload.audio_path)
    request = payload.to_orchestration_request()
    orchestrator = _get_orchestrator()
    started = time.perf_counter()
    result = orchestrator.run_agents(request)
    result["session_id"] = payload.session_id
    result["processing_time_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
    return result


@router.post("/trust", summary="Detectif.ai + Adaptive Trust Engine evaluation")
async def trust_evaluate(
    payload: OrchestrationPayload,
    x_n8n_secret: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _check_phase3_secret(x_n8n_secret)
    payload.audio_path = _safe_phase3_audio_path(payload.audio_path)
    request = payload.to_orchestration_request()
    orchestrator = _get_orchestrator()
    started = time.perf_counter()
    errors: List[str] = []

    audio_report_dict = orchestrator.precheck(request)
    audio_report = _audio_report_from_dict(audio_report_dict)
    if audio_report is None:
        raise HTTPException(status_code=500, detail="Audio report could not be constructed")
    if not audio_report_dict.get("audio_available"):
        errors.append("audio_precheck_unavailable")

    if request.agent_findings:
        agent_findings = request.agent_findings
        activated_agents = list(agent_findings.keys())
    else:
        agent_result = orchestrator.run_agents(request)
        agent_findings = agent_result["agent_findings"]
        activated_agents = agent_result["activated_agents"]
        errors.extend(agent_result["errors"])

    evidence = orchestrator.resolve_evidence(request)
    if evidence.get("detection_error"):
        errors.append(f"detectif: {evidence['detection_error']}")
    trust = orchestrator.evaluate_trust(request, audio_report, evidence)
    language = _normalize_language(
        request.preferred_language
        or (agent_findings.get("regional_language", {}).get("findings") or {}).get("preferred_recovery_language")
    )
    deterministic_plan = _build_plan(
        verification_status=trust.get("verification_status"),
        decision=trust.get("decision"),
        session_state=trust.get("session_state"),
        reason_codes=trust.get("reason_codes"),
        legacy_recovery_action=trust.get("recovery_action"),
        agent_findings=agent_findings,
        preferred_language=language,
    )

    aletheia = evidence.get("aletheia")
    eidos = evidence.get("eidos")
    return {
        "session_id": payload.session_id,
        "activated_agents": activated_agents,
        "agent_findings": agent_findings,
        "detection_result": {
            "provider": evidence.get("provider"),
            "configured": evidence.get("detection_configured"),
            "status": getattr(aletheia, "status", EvidenceStatus.UNAVAILABLE).value if aletheia else EvidenceStatus.UNAVAILABLE.value,
            "liveness_score": getattr(aletheia, "liveness_score", None),
            "confidence": getattr(aletheia, "confidence", None),
            "error": evidence.get("detection_error"),
            "simulation": evidence.get("simulation", False),
        },
        "identity_result": {
            "status": getattr(eidos, "status", EvidenceStatus.UNAVAILABLE).value if eidos else EvidenceStatus.UNAVAILABLE.value,
            "match_score": getattr(eidos, "match_score", None),
            "confidence": getattr(eidos, "confidence", None),
            "cross_language": agent_findings.get("cross_language_identity", {}).get("findings"),
        },
        "outcome": trust.get("outcome"),
        "trust_decision": {
            "outcome": trust.get("outcome"),
            "verification_status": trust.get("verification_status"),
            "decision": trust.get("decision"),
            "session_state": trust.get("session_state"),
            "reason_codes": trust.get("reason_codes", []),
            "conflicting_evidence": trust.get("conflicting_evidence", False),
            "independent_auth_required": trust.get("independent_auth_required", True),
            "sensitive_operations_paused": trust.get("sensitive_operations_paused", True),
            "terminal_state": trust.get("terminal_state", False),
            "attempt_number": trust.get("attempt_number"),
            "evidence_summary": trust.get("evidence_summary"),
            "security_restrictions": trust.get("security_restrictions"),
        },
        "decision_reasons": trust.get("reason_codes", []),
        "recovery_action": deterministic_plan.action,
        "customer_message": deterministic_plan.customer_message,
        "preferred_language": language,
        "audio_quality": audio_report_dict,
        "errors": errors,
        "simulation_mode": evidence.get("simulation", False),
        "processing_time_ms": round((time.perf_counter() - started) * 1000.0, 2),
    }


@router.post("/recovery", summary="Deterministic recovery + validated Gemini phrasing")
async def recovery_generate(
    payload: RecoveryPayload,
    x_n8n_secret: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _check_phase3_secret(x_n8n_secret)
    orchestrator = _get_orchestrator()
    request = _OrchestrationRequest(
        session_id=payload.session_id,
        preferred_language=payload.preferred_language,
        agent_findings=payload.agent_findings,
        use_gemini=payload.use_gemini,
    )
    trust = {
        "verification_status": payload.verification_status,
        "decision": payload.decision,
        "session_state": payload.session_state,
        "reason_codes": payload.reason_codes,
        "recovery_action": payload.recovery_action,
    }
    started = time.perf_counter()
    recovery = orchestrator.build_recovery(
        request,
        trust,
        payload.agent_findings or {},
        _normalize_language(payload.preferred_language),
        use_gemini=payload.use_gemini,
    )
    recovery["processing_time_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
    recovery.setdefault("gemini_used", False)
    return recovery


@router.post("/orchestrate", summary="Full Phase 3 orchestration pipeline")
async def orchestrate(
    payload: OrchestrationPayload,
    x_n8n_secret: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _check_phase3_secret(x_n8n_secret)
    payload.audio_path = _safe_phase3_audio_path(payload.audio_path)
    result = _get_orchestrator().orchestrate(
        payload.to_orchestration_request(),
        use_gemini=payload.use_gemini,
    )
    return result.payload
