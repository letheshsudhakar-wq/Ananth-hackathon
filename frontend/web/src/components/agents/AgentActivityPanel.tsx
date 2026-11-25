/**
 * src/components/agents/AgentActivityPanel.tsx
 * ANANTH Phase 4 — Live agent activity panel.
 * Shows real agent execution status from the orchestrator.
 * Never fabricates progress or outcomes.
 */
import React from 'react';
import {
  CheckCircle2,
  CircleDashed,
  AlertTriangle,
  XCircle,
  Minus,
  Loader2,
  Shield,
  Cpu,
  Mic2,
  WifiOff,
  Globe2,
  Languages,
  Eye,
  Brain,
  RefreshCcw,
} from 'lucide-react';
import type { AgentState, AgentStatus, VerificationPhase } from '@/hooks/useOrchestration';

interface AgentActivityPanelProps {
  phase: VerificationPhase;
  agentStates: AgentState[];
  processingTimeMs?: number;
  simulationMode?: boolean;
  activatedCount?: number;
}

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  speech_sufficiency: Mic2,
  acoustic_intelligence: Cpu,
  network_resilience: WifiOff,
  regional_language: Globe2,
  cross_language_identity: Languages,
};

const SYSTEM_AGENTS = [
  { key: 'aletheia', label: 'Aletheia · Liveness', icon: Eye },
  { key: 'eidos', label: 'Eidos · Voiceprint', icon: Brain },
  { key: 'trust_engine', label: 'Adaptive Trust Engine', icon: Shield },
  { key: 'recovery', label: 'Recovery Agent', icon: RefreshCcw },
];

function statusColor(s: AgentStatus): string {
  switch (s) {
    case 'processing': return 'text-violet-400';
    case 'completed':  return 'text-emerald-400';
    case 'warning':    return 'text-amber-400';
    case 'failed':     return 'text-red-400';
    case 'not_required': return 'text-slate-600';
    default:           return 'text-slate-500';
  }
}

function StatusIcon({ status }: { status: AgentStatus }) {
  switch (status) {
    case 'processing':   return <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />;
    case 'completed':    return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    case 'warning':      return <AlertTriangle className="w-4 h-4 text-amber-400" />;
    case 'failed':       return <XCircle className="w-4 h-4 text-red-400" />;
    case 'not_required': return <Minus className="w-4 h-4 text-slate-600" />;
    default:             return <CircleDashed className="w-4 h-4 text-slate-500" />;
  }
}

function statusLabel(s: AgentStatus): string {
  switch (s) {
    case 'processing':   return 'Processing';
    case 'completed':    return 'Complete';
    case 'warning':      return 'Warning';
    case 'failed':       return 'Failed';
    case 'not_required': return 'Not Required';
    default:             return 'Waiting';
  }
}

function systemAgentStatus(phase: VerificationPhase): AgentStatus {
  if (phase === 'processing' || phase === 'uploading') return 'processing';
  if (phase === 'done') return 'completed';
  if (phase === 'error') return 'failed';
  return 'waiting';
}

export function AgentActivityPanel({
  phase,
  agentStates,
  processingTimeMs,
  simulationMode,
  activatedCount,
}: AgentActivityPanelProps) {
  const sysStatus = systemAgentStatus(phase);

  return (
    <div className="card space-y-1.5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[rgb(var(--text-primary))]">
          Agent Activity
        </h3>
        <div className="flex items-center gap-2">
          {simulationMode && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-400/10 text-amber-300 border border-amber-400/20">
              Simulation
            </span>
          )}
          {processingTimeMs != null && (
            <span className="text-[10px] font-mono text-[rgb(var(--text-muted))]">
              {processingTimeMs.toFixed(0)} ms
            </span>
          )}
        </div>
      </div>

      {/* Master Orchestrator row */}
      <div className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg bg-violet-500/8 border border-violet-500/15">
        <Shield className="w-4 h-4 text-violet-400 shrink-0" />
        <span className="flex-1 text-xs font-medium text-[rgb(var(--text-primary))]">
          Master Orchestrator
        </span>
        {phase === 'uploading' || phase === 'processing' ? (
          <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
        ) : phase === 'done' ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        ) : phase === 'error' ? (
          <XCircle className="w-4 h-4 text-red-400" />
        ) : (
          <CircleDashed className="w-4 h-4 text-slate-500" />
        )}
        <span className={`text-[10px] w-20 text-right ${phase === 'done' ? 'text-emerald-400' : 'text-[rgb(var(--text-muted))]'}`}>
          {phase === 'uploading' ? 'Uploading' : phase === 'processing' ? 'Coordinating' : phase === 'done' ? `${activatedCount ?? 0} activated` : phase === 'error' ? 'Failed' : 'Idle'}
        </span>
      </div>

      {/* 5 specialized agents */}
      {agentStates.map((agent) => {
        const Icon = ICON_MAP[agent.key] ?? Cpu;
        return (
          <div
            key={agent.key}
            className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition-colors ${
              agent.status === 'not_required' ? 'opacity-40' : 'bg-[var(--hover-bg)]'
            }`}
          >
            <Icon className={`w-3.5 h-3.5 shrink-0 ${statusColor(agent.status)}`} />
            <span className="flex-1 text-xs text-[rgb(var(--text-secondary))]">{agent.label}</span>
            <StatusIcon status={agent.status} />
            <div className="text-right min-w-[80px]">
              <div className={`text-[10px] ${statusColor(agent.status)}`}>
                {statusLabel(agent.status)}
              </div>
              {agent.summary && agent.status !== 'waiting' && agent.status !== 'not_required' && (
                <div className="text-[9px] text-[rgb(var(--text-muted))] truncate max-w-[80px]">
                  {agent.summary}
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* System agents (Aletheia, Eidos, Trust Engine, Recovery) */}
      <div className="border-t border-[rgb(var(--border-subtle))] pt-1.5 mt-1.5 space-y-1.5">
        {SYSTEM_AGENTS.map(({ key, label, icon: Icon }) => (
          <div key={key} className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg bg-[var(--hover-bg)]">
            <Icon className={`w-3.5 h-3.5 shrink-0 ${statusColor(sysStatus)}`} />
            <span className="flex-1 text-xs text-[rgb(var(--text-secondary))]">{label}</span>
            <StatusIcon status={sysStatus} />
            <span className={`text-[10px] w-20 text-right ${statusColor(sysStatus)}`}>
              {statusLabel(sysStatus)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
