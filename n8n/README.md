# ANANTH — n8n Multi-Agent Orchestration Layer

**Track 03 – The Trust Layer | UNCLONE by Detectif.ai**

This directory hosts the self-hosted **n8n Community Edition** multi-agent orchestration architecture for ANANTH.

---

## 1. Directory Structure

```text
n8n/
├── .env.example                                # Template for local environment settings
├── README.md                                   # Setup & execution instructions
└── workflows/
    ├── ananth_foundation_workflow.json         # Foundation Webhook -> Backend bridge workflow
    ├── agent1_speech_sufficiency.json          # Agent 1: Speech Sufficiency
    ├── agent2_acoustic_intelligence.json       # Agent 2: Acoustic Intelligence
    ├── agent3_network_resilience.json          # Agent 3: Network Resilience
    ├── agent4_regional_language.json           # Agent 4: Regional Language
    ├── agent5_cross_language_identity.json     # Agent 5: Cross-Language Identity
    ├── master-orchestrator.json                # Phase 3: full pipeline (webhook entry point)
    ├── trust-engine-integration.json           # Phase 3: Detectif.ai -> Trust Engine
    └── recovery-agent.json                     # Phase 3: deterministic recovery + Gemini phrasing
```

---

## 2. Multi-Agent Orchestration Roadmap

n8n serves as the cognitive state coordinator managing five specialized sub-agents powered by shared Gemini intelligence:

1. **Speech Sufficiency Agent**: Identifies brief voice bursts and prompts targeted conversational speech.
2. **Acoustic Intelligence Agent**: Isolates background noise anomalies and directs environment mitigation.
3. **Network Resilience Agent**: Detects latency/packet loss and regulates streaming bitrates.
4. **Regional Language Agent**: Detects and adapts to Indian regional languages and accents.
5. **Cross-Language Identity Agent**: Verifies vocal tract acoustic invariance across language switching.

---

## 3. Phase 3 Master Orchestration

The Phase 3 workflows coordinate all five specialized agents, Detectif.ai evidence and the Adaptive Trust Engine. They call stable backend HTTP paths instead of n8n Execute Workflow IDs, so they keep working after import.

| Workflow | Webhook path | Backend stages |
| --- | --- | --- |
| `master-orchestrator.json` | `POST /webhook/ananth/orchestrate` | `/v1/n8n/prechecks` → `/v1/n8n/agents/batch` → `/v1/n8n/trust` → `/v1/n8n/recovery` |
| `trust-engine-integration.json` | `POST /webhook/ananth/trust/evaluate` | `/v1/n8n/trust` |
| `recovery-agent.json` | `POST /webhook/ananth/recovery/generate` | `/v1/n8n/recovery` |

Pipeline: Webhook → Validation → Audio Pre-checks → Agent Routing → Specialized Agents (concurrent) → Detectif.ai → Adaptive Trust Engine → Gemini Recovery → Unified Response.

- The Trust Engine alone returns `VERIFIED`, `RECOVERY_REQUIRED` or `BLOCKED`.
- Gemini Flash only phrases an approved recovery action. It never sees audio, never changes scores and never overrides security decisions.
- Missing evidence, provider failures and malformed LLM output fall back deterministically; none of them can produce a successful verification.
- Audio is uploaded once to `/v1/n8n/session/{session_id}/audio`; workflows pass only `session_id` and structured metadata.

Set `ANANTH_BACKEND_URL` and (optionally) `N8N_BRIDGE_SECRET` in the n8n environment. Gemini and Detectif.ai credentials stay in the Python backend environment (`GEMINI_API_KEY`, `GEMINI_MODEL`, `DETECTIF_API_URL`, `DETECTIF_API_KEY`); see `.env.example`.

Import order: the five agent workflows, then `trust-engine-integration.json` and `recovery-agent.json`, then `master-orchestrator.json`. Activate each workflow after saving.

---

## 4. How to Run n8n Locally (Windows Setup)

### Option A: Direct Node.js / npx (Recommended for Windows)
No Docker required. Run directly using the installed Node.js runtime:

```powershell
# In PowerShell (Port 5678)
npx n8n
```
Once started, open your browser to **http://localhost:5678/**.

### Option B: Docker (If Docker Desktop is installed)
```powershell
docker run -it --rm --name ananth-n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

---

## 5. Importing the Foundation Workflow

1. Open **http://localhost:5678/**.
2. In the left navigation menu, click **Workflows** $\rightarrow$ **Add Workflow**.
3. In the top-right menu (`...`), click **Import from File**.
4. Select `n8n/workflows/ananth_foundation_workflow.json`.
5. Click **Save** and toggle the workflow to **Active**.

---

## 6. Security & Biometric Privacy Safeguards

- **Zero Biometric Raw Audio to LLM**: Raw audio recordings and embeddings are **never** passed to external LLM services or n8n nodes. Only acoustic metadata (SNR, duration, clipping percentage) and normalized decision metrics are orchestrated.
- **Fail-Closed Integration**: If the backend is unreachable or an agent times out, n8n fails closed by enforcing secondary multi-factor challenge or manual escalation.
