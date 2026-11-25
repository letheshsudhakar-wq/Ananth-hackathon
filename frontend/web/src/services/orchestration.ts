/**
 * src/services/orchestration.ts
 * ANANTH Phase 4 — Multi-Agent Orchestration API client.
 * All calls go through the Python backend; n8n webhooks are never exposed.
 */
import { apiClient } from './api';

export type AgentOutcome = 'VERIFIED' | 'RECOVERY_REQUIRED' | 'BLOCKED';

export type AgentFindingKey =
  | 'speech_sufficiency'
  | 'acoustic_intelligence'
  | 'network_resilience'
  | 'regional_language'
  | 'cross_language_identity';

export interface AgentFinding {
  agent_name?: string;
  status?: string;
  sufficient?: boolean;
  quality_status?: string;
  integrity_status?: string;
  language_detected?: string;
  language_match?: boolean;
  processing_time_ms?: number;
  findings?: Record<string, unknown>;
  measurements?: Record<string, number | string | boolean | null>;
  confidence?: number;
  limitations?: string[];
  recommended_action?: string;
  error?: string;
  [key: string]: unknown;
}

export interface OrchestrationPayload {
  session_id: string;
  caller_id?: string;
  action_risk?: 'LOW' | 'MEDIUM' | 'HIGH' | 'FINANCIAL';
  audio_path?: string;
  preferred_language?: string;
  use_gemini?: boolean;
  simulation_mode?: boolean;
  agent_timeout_seconds?: number;
}

export interface OrchestrationResult {
  session_id: string;
  outcome: AgentOutcome;
  verification_status: string;
  decision: string;
  session_state: string;
  activated_agents: string[];
  agent_findings: Partial<Record<AgentFindingKey, AgentFinding>>;
  detection_result: Record<string, unknown>;
  trust_decision: Record<string, unknown>;
  recovery_action: string | null;
  customer_message: string | null;
  preferred_language: string;
  processing_time_ms: number;
  agent_processing_time_ms: number;
  errors: string[];
  simulation_mode: boolean;
  reason_codes: string[];
  independent_auth_required: boolean;
  sensitive_operations_paused: boolean;
  terminal_state: boolean;
  recovery_details?: Record<string, unknown>;
}

export interface AudioUploadResult {
  session_id: string;
  audio_path: string;
  size_bytes: number;
  audio_available: boolean;
  processing_time_ms: number;
}

export interface RecoveryPayload {
  session_id: string;
  verification_status?: string;
  decision?: string;
  session_state?: string;
  reason_codes?: string[];
  preferred_language?: string;
  use_gemini?: boolean;
}

export interface RecoveryResult {
  recovery_action: string;
  customer_message: string;
  gemini_used: boolean;
  processing_time_ms: number;
}

// ── Upload audio for a session ─────────────────────────────────────────────
export async function uploadSessionAudio(
  sessionId: string,
  audioBlob: Blob,
  filename = audioBlob instanceof File ? audioBlob.name : 'recording.webm'
): Promise<AudioUploadResult> {
  const form = new FormData();
  form.append('file', new File([audioBlob], filename, { type: audioBlob.type || 'audio/webm' }));
  const res = await apiClient.post<AudioUploadResult>(
    `/v1/n8n/session/${encodeURIComponent(sessionId)}/audio`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 30000 }
  );
  return res.data;
}

// ── Run full orchestration pipeline ───────────────────────────────────────
export async function runOrchestration(
  payload: OrchestrationPayload
): Promise<OrchestrationResult> {
  const res = await apiClient.post<OrchestrationResult>('/v1/n8n/orchestrate', payload, {
    timeout: 60000,
  });
  return res.data;
}

// ── Fetch recovery instructions ────────────────────────────────────────────
export async function fetchRecovery(payload: RecoveryPayload): Promise<RecoveryResult> {
  const res = await apiClient.post<RecoveryResult>('/v1/n8n/recovery', payload, {
    timeout: 15000,
  });
  return res.data;
}

// ── n8n health check ───────────────────────────────────────────────────────
export async function getN8nHealth(): Promise<{ status: string; agents: string[] }> {
  const res = await apiClient.get('/v1/n8n/health', { timeout: 5000 });
  return res.data;
}

// ── Generate a collision-resistant session ID ──────────────────────────────
export function newSessionId(): string {
  const ts = Date.now().toString(36);
  const rnd = Math.random().toString(36).slice(2, 8);
  return `ses_${ts}_${rnd}`;
}
