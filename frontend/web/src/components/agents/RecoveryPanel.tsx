/**
 * src/components/agents/RecoveryPanel.tsx
 * ANANTH Phase 4 — Recovery instructions panel.
 * Displays Gemini-generated or template recovery messages.
 * Never fabricates outcomes; shown only when outcome = RECOVERY_REQUIRED.
 */
import React from 'react';
import { RefreshCcw, Mic, Upload, Wifi, Globe2, UserCheck, MessageSquare } from 'lucide-react';

interface RecoveryPanelProps {
  outcome: string;
  recoveryAction: string | null;
  customerMessage: string | null;
  geminiUsed?: boolean;
  onRetry?: () => void;
  onRecordAgain?: () => void;
}

const ACTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  COLLECT_ADDITIONAL_SPEECH: Mic,
  RECORD_AGAIN: RefreshCcw,
  IMPROVE_ENVIRONMENT: Globe2,
  RETRY_UPLOAD: Upload,
  CONTINUE_IN_PREFERRED_LANGUAGE: Globe2,
  INDEPENDENT_VERIFICATION: UserCheck,
  HUMAN_REVIEW: UserCheck,
  PROVIDE_PASSPHRASE: Mic,
};

const ACTION_LABELS: Record<string, string> = {
  COLLECT_ADDITIONAL_SPEECH: 'Collect Additional Speech',
  RECORD_AGAIN: 'Record Again',
  IMPROVE_ENVIRONMENT: 'Improve Environment',
  RETRY_UPLOAD: 'Retry Upload',
  CONTINUE_IN_PREFERRED_LANGUAGE: 'Switch Language',
  INDEPENDENT_VERIFICATION: 'Independent Verification',
  HUMAN_REVIEW: 'Human Review',
  PROVIDE_PASSPHRASE: 'Provide Passphrase',
};

export function RecoveryPanel({
  outcome,
  recoveryAction,
  customerMessage,
  geminiUsed,
  onRetry,
  onRecordAgain,
}: RecoveryPanelProps) {
  if (outcome === 'VERIFIED') return null;
  if (outcome === 'BLOCKED') {
    return (
      <div className="card border border-red-400/20 bg-red-400/5 space-y-3">
        <div className="flex items-center gap-2.5">
          <UserCheck className="w-5 h-5 text-red-400 shrink-0" />
          <div>
            <div className="text-sm font-semibold text-red-300">Independent Verification Required</div>
            <div className="text-xs text-[rgb(var(--text-muted))] mt-0.5">
              A security policy violation or threat was detected. Human review has been initiated.
              Do not share sensitive information.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const ActionIcon = (recoveryAction && ACTION_ICONS[recoveryAction]) ?? MessageSquare;
  const actionLabel = (recoveryAction && ACTION_LABELS[recoveryAction]) ?? 'Recovery Required';

  const canRetry =
    recoveryAction &&
    ['COLLECT_ADDITIONAL_SPEECH', 'RECORD_AGAIN', 'RETRY_UPLOAD', 'PROVIDE_PASSPHRASE'].includes(
      recoveryAction
    );

  const isRecord = recoveryAction === 'RECORD_AGAIN' || recoveryAction === 'COLLECT_ADDITIONAL_SPEECH';

  return (
    <div className="card border border-amber-400/20 bg-amber-400/5 space-y-4">
      <div className="flex items-center gap-2.5">
        <ActionIcon className="w-5 h-5 text-amber-400 shrink-0" />
        <div>
          <div className="text-sm font-semibold text-amber-300">{actionLabel}</div>
          {geminiUsed && (
            <div className="text-[10px] text-[rgb(var(--text-muted))] mt-0.5">
              ✦ Gemini-assisted recovery message
            </div>
          )}
        </div>
      </div>

      {customerMessage && (
        <div className="rounded-lg bg-[var(--hover-bg)] px-4 py-3 text-sm text-[rgb(var(--text-secondary))] leading-relaxed">
          {customerMessage}
        </div>
      )}

      {canRetry && (
        <div className="flex gap-2 flex-wrap">
          {isRecord && onRecordAgain && (
            <button onClick={onRecordAgain} className="btn btn-primary btn-sm">
              <Mic className="w-3.5 h-3.5" /> Record Again
            </button>
          )}
          {onRetry && (
            <button onClick={onRetry} className="btn btn-outline btn-sm">
              <RefreshCcw className="w-3.5 h-3.5" /> Try Again
            </button>
          )}
        </div>
      )}
    </div>
  );
}
