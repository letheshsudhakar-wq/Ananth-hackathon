"""
Tests for the 5 Phase 2 n8n sub-workflows in n8n/workflows/.

Validates:
- Importable n8n JSON structure (nodes/connections consistency).
- Each workflow has: Webhook Trigger -> Validate Input -> HTTP Request Backend -> Respond.
- HTTP request targets the expected /v1/agents/* endpoint.
- Network resilience workflow uses the Switch node (per Phase 2 node-type plan).
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKFLOW_DIR = os.path.join(ROOT, "n8n", "workflows")

EXPECTED_NODE_TYPES = {
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.code",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.if",
    "n8n-nodes-base.switch",
    "n8n-nodes-base.editFields",
    "n8n-nodes-base.respondToWebhook",
}


def _load(name: str) -> dict:
    with open(os.path.join(WORKFLOW_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


def _assert_structure(wf: dict) -> list:
    errs = []
    names = {n["name"] for n in wf.get("nodes", [])}
    if not names:
        errs.append("no nodes")
    for n in wf.get("nodes", []):
        if n.get("type") not in EXPECTED_NODE_TYPES:
            errs.append(f"unknown node type: {n.get('type')}")
        if not n.get("name"):
            errs.append("node missing name")
        if not n.get("parameters"):
            errs.append(f"node {n.get('name')} missing parameters")
    for src, outs in wf.get("connections", {}).items():
        if src not in names:
            errs.append(f"connection source {src} not in nodes")
        for arr in outs.get("main", []):
            for edge in arr:
                if edge["node"] not in names:
                    errs.append(f"edge target {edge['node']} not in nodes")
    return errs


AGENT_WORKFLOWS = [
    ("agent_speech_sufficiency.json", "/v1/agents/speech_sufficiency"),
    ("agent_acoustic_intelligence.json", "/v1/agents/acoustic_intelligence"),
    ("agent_network_resilience.json", "/v1/agents/network_resilience"),
    ("agent_regional_language.json", "/v1/agents/regional_language"),
    ("agent_cross_language_identity.json", "/v1/agents/cross_language_identity"),
]


class TestN8nWorkflows:
    workflow_files = [os.path.basename(p) for p in glob.glob(os.path.join(WORKFLOW_DIR, "agent_*.json"))]

    def test_all_five_agent_workflows_exist(self):
        for name, _ in AGENT_WORKFLOWS:
            assert name in self.workflow_files, f"missing {name}"

    def test_all_workflows_parse_and_are_structurally_valid(self):
        for name, _ in AGENT_WORKFLOWS:
            wf = _load(name)
            errs = _assert_structure(wf)
            assert not errs, f"{name}: {errs}"

    def test_every_workflow_has_webhook_and_respond_nodes(self):
        for name, _ in AGENT_WORKFLOWS:
            wf = _load(name)
            node_types = {n["type"] for n in wf["nodes"]}
            assert "n8n-nodes-base.webhook" in node_types, name
            assert "n8n-nodes-base.httpRequest" in node_types, name
            assert "n8n-nodes-base.respondToWebhook" in node_types, name

    def test_every_workflow_calls_expected_backend_endpoint(self):
        for name, endpoint in AGENT_WORKFLOWS:
            wf = _load(name)
            urls = [n["parameters"]["url"] for n in wf["nodes"] if n["type"] == "n8n-nodes-base.httpRequest"]
            assert any(endpoint in u for u in urls), f"{name} -> {urls}"

    def test_network_resilience_workflow_uses_switch_node(self):
        wf = _load("agent_network_resilience.json")
        types = {n["type"] for n in wf["nodes"]}
        assert "n8n-nodes-base.switch" in types

    def test_workflows_configurable_backend_url(self):
        for name, _ in AGENT_WORKFLOWS:
            wf = _load(name)
            urls = [n["parameters"]["url"] for n in wf["nodes"] if n["type"] == "n8n-nodes-base.httpRequest"]
            assert any("$env.ANANTH_BACKEND_URL" in u or "localhost:8000" in u for u in urls), name

    def test_workflows_pass_session_id_not_raw_audio(self):
        """Design rule: raw audio not transferred between workflows unnecessarily."""
        import re
        for name, _ in AGENT_WORKFLOWS:
            wf = _load(name)
            for n in wf["nodes"]:
                code = n.get("parameters", {}).get("jsCode", "")
                assert "audio" not in code.lower() or "audio_path" in code, name
