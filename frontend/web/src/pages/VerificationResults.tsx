/**
 * src/pages/VerificationResults.tsx  (Phase 4 — real orchestration results)
 * Displays VERIFIED / RECOVERY_REQUIRED / BLOCKED from the Trust Engine.
 * Never shows VERIFIED unless the Trust Engine deterministically approved it.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ShieldCheck, ShieldAlert, ShieldX, Download, History, RotateCcw, LayoutDashboard,
  Clock, Cpu, AlertTriangle, CheckCircle2,
} from 'lucide-react';
import type { OrchestrationResult } from '@/services/orchestration';
import { AgentActivityPanel } from '@/components/agents/AgentActivityPanel';
import { AgentReports } from '@/components/agents/AgentReports';
import { RecoveryPanel } from '@/components/agents/RecoveryPanel';

function buildAgentStatesFromResult(result: OrchestrationResult) {
  const AGENT_MAP: { key: string; label: string }[] = [
    { key: 'speech_sufficiency', label: 'Speech Sufficiency' },
    { key: 'acoustic_intelligence', label: 'Acoustic Intelligence' },
    { key: 'network_resilience', label: 'Network Resilience' },
    { key: 'regional_language', label: 'Regional Language' },
    { key: 'cross_language_identity', label: 'Cross-Language Identity' },
  ];
  return AGENT_MAP.map(({ key, label }) => {
    const finding = (result.agent_findings?.[key as keyof typeof result.agent_findings] ?? {}) as Record<string, unknown>;
    const activated = (result.activated_agents ?? []).some((a) =>
      a.toLowerCase().replace(/[\s_-]/g, '').includes(key.replace(/_/g, ''))
    );
    if (!activated && Object.keys(finding).length === 0) {
      return { key, label, status: 'not_required' as const };
    }
    const err = finding?.error as string | undefined;
    const s = (finding?.status as string | undefined)?.toLowerCase() ?? '';
    let status: 'completed' | 'warning' | 'failed' = 'completed';
    if (err && err !== 'null') status = 'warning';
    if (s.includes('fail') || s.includes('error')) status = 'failed';
    return { key, label, status };
  });
}

const OUTCOME_CONFIG = {
  VERIFIED: {
    icon: ShieldCheck,
    color: 'emerald',
    label: 'Verified',
    description: 'Authentication requirements satisfied by the Trust Engine.',
    border: 'border-emerald-400/20',
    iconColor: 'text-emerald-400',
    textColor: 'text-emerald-300',
  },
  RECOVERY_REQUIRED: {
    icon: ShieldAlert,
    color: 'amber',
    label: 'Additional Verification Required',
    description: 'Further evidence or independent verification is needed.',
    border: 'border-amber-400/20',
    iconColor: 'text-amber-400',
    textColor: 'text-amber-300',
  },
  BLOCKED: {
    icon: ShieldX,
    color: 'red',
    label: 'Blocked',
    description: 'A security threat or policy violation was detected.',
    border: 'border-red-400/20',
    iconColor: 'text-red-400',
    textColor: 'text-red-300',
  },
} as const;

export function VerificationResults() {
  const navigate = useNavigate();
  const [result, setResult] = useState<OrchestrationResult | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem('ananth-orch-result');
    if (raw) {
      try { setResult(JSON.parse(raw)); } catch { /* ignore */ }
    }
  }, []);

  if (!result) {
    return (
      <div className="max-w-6xl mx-auto space-y-5">
        <div>
          <h1 className="text-xl font-semibold">Verification Results</h1>
          <p className="text-sm text-[rgb(var(--text-muted))] mt-1">No results available.</p>
        </div>
        <div className="card flex flex-col items-center py-12 gap-4 text-center">
          <AlertTriangle className="w-10 h-10 text-amber-400" />
          <p className="text-sm text-[rgb(var(--text-secondary))]">
            No verification session found. Please start a new verification.
          </p>
          <button onClick={() => navigate('/voice-verification')} className="btn btn-primary">
            <RotateCcw className="w-4 h-4" /> Start Verification
          </button>
        </div>
      </div>
    );
  }

  const outcome = (result.outcome ?? 'RECOVERY_REQUIRED') as keyof typeof OUTCOME_CONFIG;
  const cfg = OUTCOME_CONFIG[outcome] ?? OUTCOME_CONFIG.RECOVERY_REQUIRED;
  const OutcomeIcon = cfg.icon;
  const agentStates = buildAgentStatesFromResult(result);

  const download = () => {
    const lines = [
      'ANANTH — Voice Authentication Report',
      `Session ID:  ${result.session_id}`,
      `Outcome:     ${outcome}`,
      `Decision:    ${result.decision ?? 'N/A'}`,
      `Status:      ${result.verification_status ?? 'N/A'}`,
      `Processing:  ${result.processing_time_ms?.toFixed(1) ?? '?'} ms`,
      `Simulation:  ${result.simulation_mode ? 'YES (no real API keys configured)' : 'NO'}`,
      '',
      'Activated Agents: ' + (result.activated_agents ?? []).join(', '),
      '',
      'Reason Codes: ' + (result.reason_codes ?? []).join(', '),
      '',
      result.customer_message ? `Recovery Message:\n${result.customer_message}` : '',
      '',
      '— Trust Engine decision is authoritative. —',
      'No biometric data stored or transmitted externally.',
    ].join('\n');
    const blob = new Blob([lines], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `ananth-${result.session_id}.txt`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">Verification Results</h1>
          <p className="text-xs text-[rgb(var(--text-muted))] mt-1 font-mono">{result.session_id}</p>
        </div>
        {result.simulation_mode && (
          <span className="text-xs px-2 py-1 rounded-full bg-amber-400/10 text-amber-300 border border-amber-400/20">
            Simulation Mode
          </span>
        )}
      </div>

      <div className="grid lg:grid-cols-[320px_1fr] gap-5">
        {/* Outcome card */}
        <section className={`card flex flex-col items-center text-center py-8 border ${cfg.border}`}>
          <OutcomeIcon className={`w-16 h-16 ${cfg.iconColor}`} />
          <h2 className={`text-xl font-bold mt-4 ${cfg.textColor}`}>{cfg.label}</h2>
          <p className="text-xs text-[rgb(var(--text-muted))] mt-2 max-w-[200px]">{cfg.description}</p>

          {/* Metrics */}
          <div className="mt-6 w-full space-y-2 text-left border-t border-[rgb(var(--border-subtle))] pt-4">
            {[
              ['Decision', result.decision ?? 'N/A'],
              ['Status', result.verification_status ?? 'N/A'],
              ['Agents', `${result.activated_agents?.length ?? 0} activated`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs border-b border-[rgb(var(--border-subtle))] pb-1.5">
                <span className="text-[rgb(var(--text-muted))]">{k}</span>
                <span className="font-medium">{v}</span>
              </div>
            ))}
            <div className="flex justify-between text-xs pt-0.5">
              <span className="text-[rgb(var(--text-muted))] flex items-center gap-1"><Clock className="w-3 h-3" /> Time</span>
              <span className="font-mono text-xs">{result.processing_time_ms?.toFixed(1)} ms</span>
            </div>
          </div>
        </section>

        {/* Right column */}
        <div className="space-y-4">
          {/* Reason codes */}
          {result.reason_codes?.length > 0 && (
            <div className="card">
              <h2 className="font-semibold mb-3 text-sm flex items-center gap-2">
                <Cpu className="w-4 h-4 text-[rgb(var(--accent-soft))]" /> Trust Engine Findings
              </h2>
              <div className="flex flex-wrap gap-2">
                {result.reason_codes.map((rc) => (
                  <span key={rc} className="text-xs px-2.5 py-1 rounded-full bg-[var(--hover-bg)] border border-[rgb(var(--border-subtle))] font-mono">
                    {rc}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Recovery instructions */}
          {outcome !== 'VERIFIED' && (
            <RecoveryPanel
              outcome={outcome}
              recoveryAction={result.recovery_action}
              customerMessage={result.customer_message}
              onRetry={() => navigate('/voice-verification')}
              onRecordAgain={() => navigate('/voice-verification')}
            />
          )}

          {outcome === 'VERIFIED' && (
            <div className="card border border-emerald-400/20 flex items-center gap-3 py-4 px-5">
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
              <div>
                <div className="text-sm font-semibold text-emerald-300">Authentication Approved</div>
                <div className="text-xs text-[rgb(var(--text-muted))] mt-0.5">
                  The Adaptive Trust Engine has authorised this session.
                </div>
              </div>
            </div>
          )}

          {/* Agent panel */}
          <AgentActivityPanel
            phase="done"
            agentStates={agentStates}
            processingTimeMs={result.agent_processing_time_ms}
            simulationMode={result.simulation_mode}
            activatedCount={result.activated_agents?.length}
          />
        </div>
      </div>

      <AgentReports reports={result.agent_findings ?? {}} />

      {/* Action buttons */}
      <div className="flex flex-wrap gap-3">
        <button onClick={download} className="btn btn-primary">
          <Download className="w-4 h-4" /> Download Report
        </button>
        <Link to="/detection-history" className="btn btn-outline">
          <History className="w-4 h-4" /> View History
        </Link>
        <button onClick={() => navigate('/voice-verification')} className="btn btn-outline">
          <RotateCcw className="w-4 h-4" /> New Verification
        </button>
        <Link to="/dashboard" className="btn btn-ghost">
          <LayoutDashboard className="w-4 h-4" /> Dashboard
        </Link>
      </div>
    </div>
  );
}
