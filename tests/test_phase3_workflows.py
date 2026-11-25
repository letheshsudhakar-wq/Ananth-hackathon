"""Phase 3 n8n workflow structure tests (importable JSON + stage wiring)."""

from __future__ import annotations

import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKFLOW_DIR = os.path.join(ROOT, "n8n", "workflows")

ALLOWED_TYPES = {
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.code",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.if",
    "n8n-nodes-base.respondToWebhook",
}


def load(name: str) -> dict:
    with open(os.path.join(WORKFLOW_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


def node_names(wf: dict) -> set:
    return {n["name"] for n in wf["nodes"]}


def assert_valid(wf: dict) -> None:
    names = node_names(wf)
    assert names
    for node in wf["nodes"]:
        assert node["type"] in ALLOWED_TYPES, node["type"]
        assert node.get("name")
        assert node.get("parameters") is not None
        # Workflow IDs break after import; these workflows must not use them.
        assert node["type"] != "n8n-nodes-base.executeWorkflow"
    for source, outputs in wf["connections"].items():
        assert source in names
        for branch in outputs.get("main", []):
            for edge in branch:
                assert edge["node"] in names


def http_urls(wf: dict) -> list:
    return [
        n["parameters"].get("url", "")
        for n in wf["nodes"]
        if n["type"] == "n8n-nodes-base.httpRequest"
    ]


def test_master_orchestrator_exists_and_is_importable():
    wf = load("master-orchestrator.json")
    assert wf["name"].startswith("ANANTH Master Orchestrator")
    assert_valid(wf)


def test_master_orchestrator_covers_required_stages():
    wf = load("master-orchestrator.json")
    names = node_names(wf)
    expected = {
        "Webhook Trigger",
        "Validate Input",
        "Audio Pre-checks",
        "Agent Routing",
        "Specialized Agents Concurrent",
        "Detectif AI and Trust Engine",
        "Gemini Recovery",
        "Build Unified Response",
        "Respond to Webhook",
    }
    assert expected <= names


def test_master_orchestrator_calls_phase3_backend_stages():
    urls = http_urls(load("master-orchestrator.json"))
    for suffix in (
        "/v1/n8n/prechecks",
        "/v1/n8n/agents/batch",
        "/v1/n8n/trust",
        "/v1/n8n/recovery",
    ):
        assert any(suffix in url for url in urls), f"missing {suffix}: {urls}"


def test_master_orchestrator_routes_all_five_agents():
    wf = load("master-orchestrator.json")
    code = "\n".join(
        n["parameters"].get("jsCode", "")
        for n in wf["nodes"]
        if n["type"] == "n8n-nodes-base.code"
    )
    for key in (
        "speech_sufficiency",
        "acoustic_intelligence",
        "network_resilience",
        "regional_language",
        "cross_language_identity",
    ):
        assert key in code, f"agent {key} not routed"


def test_master_orchestrator_uses_session_references_not_audio_payloads():
    wf = load("master-orchestrator.json")
    for node in wf["nodes"]:
        code = node["parameters"].get("jsCode", "")
        assert "base64" not in code.lower()
        assert "audio_bytes" not in code.lower()
        assert "audio_base64" not in code.lower()


def test_trust_engine_integration_workflow():
    wf = load("trust-engine-integration.json")
    assert_valid(wf)
    assert any("/v1/n8n/trust" in url for url in http_urls(wf))
    assert "Webhook Trigger" in node_names(wf)
    assert "Respond to Webhook" in node_names(wf)


def test_recovery_agent_workflow():
    wf = load("recovery-agent.json")
    assert_valid(wf)
    assert any("/v1/n8n/recovery" in url for url in http_urls(wf))
    assert "Gemini Recovery" in node_names(wf)
    assert "Respond to Webhook" in node_names(wf)


def test_all_phase3_workflows_use_configurable_backend_url():
    for name in ("master-orchestrator.json", "trust-engine-integration.json", "recovery-agent.json"):
        urls = http_urls(load(name))
        assert urls
        assert all("$env.ANANTH_BACKEND_URL" in url for url in urls), name


def test_phase3_workflows_do_not_reference_credentials_that_break_import():
    for name in ("master-orchestrator.json", "trust-engine-integration.json", "recovery-agent.json"):
        wf = load(name)
        for node in wf["nodes"]:
            assert "credentials" not in node["parameters"], (name, node["name"])
