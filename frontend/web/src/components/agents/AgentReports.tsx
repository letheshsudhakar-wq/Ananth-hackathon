import React from 'react';
import type { AgentFinding, AgentFindingKey } from '@/services/orchestration';

interface AgentReportsProps {
  reports: Partial<Record<AgentFindingKey, AgentFinding>>;
}

const AGENTS: { key: AgentFindingKey; label: string }[] = [
  { key: 'speech_sufficiency', label: 'Speech Sufficiency' },
  { key: 'acoustic_intelligence', label: 'Acoustic Intelligence' },
  { key: 'network_resilience', label: 'Network Resilience' },
  { key: 'regional_language', label: 'Regional Language' },
  { key: 'cross_language_identity', label: 'Cross-Language Identity' },
];

function displayValue(value: unknown): string {
  if (value == null) return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function ReportFields({ title, values }: { title: string; values: Record<string, unknown> }) {
  const entries = Object.entries(values);
  if (!entries.length) return null;

  return (
    <div>
      <h4 className="text-xs font-semibold text-[rgb(var(--text-secondary))] mb-2">{title}</h4>
      <dl className="grid sm:grid-cols-2 gap-x-5 gap-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="min-w-0">
            <dt className="text-[10px] text-[rgb(var(--text-muted))]">{formatLabel(key)}</dt>
            <dd className="text-xs text-[rgb(var(--text-secondary))] break-words">
              {displayValue(value)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function AgentReports({ reports }: AgentReportsProps) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-base font-semibold">Individual Agent Reports</h2>
        <p className="text-xs text-[rgb(var(--text-muted))] mt-1">
          Each report shows the agent’s own result and supporting details.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {AGENTS.map(({ key, label }) => {
          const report = reports[key];
          const status = report?.status ?? 'NOT RUN';
          const statusColor =
            status === 'PASS'
              ? 'text-emerald-400'
              : status === 'WARNING' || status === 'INCONCLUSIVE'
                ? 'text-amber-400'
                : status === 'ERROR'
                  ? 'text-red-400'
                  : 'text-slate-400';
          const findings = report?.findings ?? {};
          const { summary, ...details } = findings;

          return (
            <article key={key} className="card space-y-4">
              <header className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold">{label}</h3>
                  {report?.agent_name && (
                    <p className="text-[10px] text-[rgb(var(--text-muted))] mt-0.5">
                      {report.agent_name}
                    </p>
                  )}
                </div>
                <span className={`text-xs font-semibold ${statusColor}`}>{status}</span>
              </header>

              {typeof summary === 'string' && (
                <p className="text-xs leading-relaxed text-[rgb(var(--text-secondary))]">
                  {summary}
                </p>
              )}

              {report ? (
                <>
                  <ReportFields title="Findings" values={details} />
                  <ReportFields
                    title="Measurements"
                    values={report.measurements ?? {}}
                  />
                  <div className="grid grid-cols-2 gap-3 border-t border-[rgb(var(--border-subtle))] pt-3">
                    <div>
                      <div className="text-[10px] text-[rgb(var(--text-muted))]">Recommendation</div>
                      <div className="text-xs text-[rgb(var(--text-secondary))]">
                        {report.recommended_action ?? '—'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-[rgb(var(--text-muted))]">Confidence / Time</div>
                      <div className="text-xs text-[rgb(var(--text-secondary))]">
                        {report.confidence == null ? '—' : `${(report.confidence * 100).toFixed(1)}%`}
                        {' / '}
                        {report.processing_time_ms == null ? '—' : `${report.processing_time_ms.toFixed(1)} ms`}
                      </div>
                    </div>
                  </div>
                  {report.limitations?.length ? (
                    <div>
                      <h4 className="text-xs font-semibold text-[rgb(var(--text-secondary))] mb-1">
                        Limitations
                      </h4>
                      <ul className="list-disc pl-4 space-y-1 text-[10px] text-[rgb(var(--text-muted))]">
                        {report.limitations.map((limitation, index) => (
                          <li key={`${index}-${limitation}`}>{limitation}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {report.error && (
                    <p className="text-xs text-red-400">Error: {report.error}</p>
                  )}
                </>
              ) : (
                <p className="text-xs text-[rgb(var(--text-muted))]">
                  No report was returned for this agent.
                </p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
