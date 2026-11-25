/**
 * src/hooks/useOrchestration.ts
 * ANANTH Phase 4 — full verification flow state machine.
 *
 * States: idle → uploading → processing → done | error
 * Prevents duplicate submissions via submittingRef.
 */
import { useCallback, useRef, useState } from 'react';
import {
  uploadSessionAudio,
  runOrchestration,
  fetchRecovery,
  newSessionId,
  type OrchestrationResult,
  type RecoveryResult,
  type AgentFindingKey,
} from '@/services/orchestration';

export type VerificationPhase = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

export type AgentStatus =
  | 'waiting'
  | 'processing'
  | 'completed'
  | 'warning'
  | 'failed'
  | 'not_required';

export interface AgentState {
  key: string;
  label: string;
  status: AgentStatus;
  processingTimeMs?: number;
  summary?: string;
}

const AGENT_DEFS: { key: AgentFindingKey | string; label: string }[] = [
  { key: 'speech_sufficiency', label: 'Speech Sufficiency' },
  { key: 'acoustic_intelligence', label: 'Acoustic Intelligence' },
  { key: 'network_resilience', label: 'Network Resilience' },
  { key: 'regional_language', label: 'Regional Language' },
  { key: 'cross_language_identity', label: 'Cross-Language Identity' },
];

function summarizeAgent(key: string, finding: Record<string, unknown>): string {
  if (key === 'speech_sufficiency') {
    const suf = finding?.sufficient;
    const dur = finding?.usable_speech_duration ?? finding?.total_duration;
    return suf === true
      ? `Sufficient speech${dur != null ? ` · ${Number(dur).toFixed(1)}s` : ''}`
      : `Insufficient speech${dur != null ? ` · ${Number(dur).toFixed(1)}s` : ''}`;
  }
  if (key === 'acoustic_intelligence') {
    const q = (finding?.quality_status as string) ?? (finding?.status as string) ?? '';
    const snr = finding?.snr_db;
    return q ? `${q}${snr != null ? ` · SNR ${Number(snr).toFixed(0)} dB` : ''}` : 'Assessed';
  }
  if (key === 'network_resilience') {
    const s = (finding?.integrity_status as string) ?? (finding?.status as string) ?? '';
    return s || 'Network checked';
  }
  if (key === 'regional_language') {
    const lang = (finding?.language_detected as string) ?? '';
    return lang ? `Detected: ${lang}` : 'Language assessed';
  }
  if (key === 'cross_language_identity') {
    const match = finding?.language_match;
    return match === true ? 'Language consistent' : match === false ? 'Language switched' : 'Identity assessed';
  }
  return 'Complete';
}

function agentStatusFromFinding(key: string, finding: Record<string, unknown>): AgentStatus {
  const err = finding?.error as string | undefined;
  if (err && err !== 'null') return 'warning';
  const s = (finding?.status as string | undefined)?.toLowerCase() ?? '';
  if (s.includes('fail') || s.includes('error')) return 'failed';
  if (s.includes('warn') || s.includes('poor') || s.includes('degraded')) return 'warning';
  return 'completed';
}

function buildAgentStates(result: OrchestrationResult): AgentState[] {
  return AGENT_DEFS.map(({ key, label }) => {
    const activated = result.activated_agents ?? [];
    const finding = (result.agent_findings?.[key as AgentFindingKey] ?? {}) as Record<string, unknown>;
    const wasActivated = activated.some((a) => a.toLowerCase().replace(/[\s_-]/g, '').includes(key.replace(/_/g, '')));
    if (!wasActivated && Object.keys(finding).length === 0) {
      return { key, label, status: 'not_required' as AgentStatus };
    }
    const status = agentStatusFromFinding(key, finding);
    return {
      key,
      label,
      status,
      processingTimeMs: finding?.processing_time_ms as number | undefined,
      summary: summarizeAgent(key, finding),
    };
  });
}

export function useOrchestration() {
  const [phase, setPhase] = useState<VerificationPhase>('idle');
  const [result, setResult] = useState<OrchestrationResult | null>(null);
  const [recovery, setRecovery] = useState<RecoveryResult | null>(null);
  const [agentStates, setAgentStates] = useState<AgentState[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState(newSessionId);
  const submittingRef = useRef(false);

  const setAllProcessing = () => {
    setAgentStates(AGENT_DEFS.map(({ key, label }) => ({ key, label, status: 'processing' as AgentStatus })));
  };

  const run = useCallback(
    async (audioBlob: Blob, opts: { language?: string; useGemini?: boolean } = {}) => {
      if (submittingRef.current) return;
      submittingRef.current = true;
      setError(null);
      setResult(null);
      setRecovery(null);

      try {
        // 1. Upload audio
        setPhase('uploading');
        setAgentStates(AGENT_DEFS.map(({ key, label }) => ({ key, label, status: 'waiting' as AgentStatus })));
        const upload = await uploadSessionAudio(sessionId, audioBlob);
        const audioPath = upload.audio_path;

        // 2. Run orchestration
        setPhase('processing');
        setAllProcessing();

        const orch = await runOrchestration({
          session_id: sessionId,
          audio_path: audioPath,
          preferred_language: opts.language ?? 'en',
          use_gemini: opts.useGemini ?? false,
          simulation_mode: !audioPath, // honest flag
          agent_timeout_seconds: 20,
        });

        // 3. Update agent states from real findings
        setAgentStates(buildAgentStates(orch));
        setResult(orch);
        setPhase('done');

        // 4. Fetch recovery if needed (non-blocking enrichment)
        if (orch.outcome === 'RECOVERY_REQUIRED' && orch.recovery_action) {
          try {
            const rec = await fetchRecovery({
              session_id: sessionId,
              verification_status: orch.verification_status,
              decision: orch.decision,
              session_state: orch.session_state,
              reason_codes: orch.reason_codes,
              preferred_language: opts.language ?? 'en',
              use_gemini: opts.useGemini ?? false,
            });
            setRecovery(rec);
          } catch {
            // non-fatal — orch already has customer_message
          }
        }
      } catch (err: unknown) {
        const msg =
          (err as { message?: string })?.message ?? 'Verification failed. Please try again.';
        setError(msg);
        setPhase('error');
        setAgentStates(AGENT_DEFS.map(({ key, label }) => ({ key, label, status: 'failed' as AgentStatus })));
      } finally {
        submittingRef.current = false;
      }
    },
    [sessionId]
  );

  const reset = useCallback(() => {
    setPhase('idle');
    setResult(null);
    setRecovery(null);
    setAgentStates([]);
    setError(null);
    submittingRef.current = false;
  }, []);

  return { phase, result, recovery, agentStates, error, sessionId, run, reset };
}
