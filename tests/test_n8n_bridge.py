"""
Tests for n8n Multi-Agent Orchestration Bridge Endpoint (/v1/n8n).
"""

import sys
import os

# Ensure backend root is on python path so 'import app' succeeds
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.schemas import VerificationStatus, TrustDecision, SessionState, ReasonCode

client = TestClient(app)


def test_n8n_bridge_health():
    """Verify /v1/n8n/health responds successfully."""
    response = client.get("/v1/n8n/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ready"] is True
    assert "service" in data


def test_n8n_bridge_legitimate_caller():
    """Test n8n webhook payload with authentic scores yields verified outcome."""
    payload = {
        "session_id": "n8n_sess_01",
        "caller_id": "caller_alice",
        "action_risk": "LOW",
        "agent_name": "speech_sufficiency_agent",
        "aletheia_liveness_score": 0.95,
        "aletheia_confidence": 0.90,
        "eidos_match_score": 0.94,
        "eidos_confidence": 0.88,
        "metadata": {"source": "n8n_flow"},
    }

    response = client.post("/v1/n8n/bridge", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["verification_status"] == VerificationStatus.VERIFIED.value
    assert data["decision"] == TrustDecision.ALLOW.value
    assert data["session_state"] == SessionState.VOICE_VERIFIED.value
    assert data["sensitive_operations_paused"] is False
    assert data["agent_routed_to"] == "speech_sufficiency_agent"


def test_n8n_bridge_deepfake_escalation():
    """Test n8n webhook payload detecting deepfake escalates immediately to DENY and blocks session."""
    payload = {
        "session_id": "n8n_sess_02",
        "caller_id": "caller_victim",
        "action_risk": "HIGH",
        "agent_name": "acoustic_intelligence_agent",
        "aletheia_liveness_score": 0.08,  # Synthetic deepfake
        "aletheia_confidence": 0.95,
        "eidos_match_score": 0.92,       # Timbre match
        "eidos_confidence": 0.90,
    }

    response = client.post("/v1/n8n/bridge", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verification_status"] == VerificationStatus.SUSPICIOUS.value
    assert data["decision"] == TrustDecision.DENY.value
    assert data["session_state"] == SessionState.BLOCKED.value
    assert data["sensitive_operations_paused"] is True
    assert ReasonCode.CREDIBLE_DEEPFAKE_DETECTED.value in data["reason_codes"]


def test_n8n_bridge_invalid_risk_fails_closed():
    """Invalid or malformed risk tiers fail closed to 400."""
    payload = {
        "session_id": "n8n_sess_03",
        "caller_id": "caller_mallory",
        "action_risk": "ILLEGAL_TIER_OVERRIDE",
    }

    response = client.post("/v1/n8n/bridge", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_RISK_TIER"


def test_n8n_bridge_missing_required_fields():
    """Missing session_id or caller_id triggers schema validation error."""
    payload = {
        "action_risk": "LOW",
    }

    response = client.post("/v1/n8n/bridge", json=payload)
    assert response.status_code == 422
