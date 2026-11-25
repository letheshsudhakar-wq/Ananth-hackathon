import React, { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Network, ShieldAlert, Radio, Loader2 } from 'lucide-react';
import { getAlerts } from '@/services/api';
import { useOrganization } from '@/context/OrganizationContext';
import type { AlertRecord } from '@/types';

export function ThreatIntelligence() {
  const { org } = useOrganization();
  const [threats, setThreats] = useState<AlertRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAlerts({ organization: org, limit: 200 })
      .then((res) => {
        if (!cancelled) setThreats(res.items.filter((item) => item.flagged));
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'Could not load threat intelligence.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [org]);

  const stats = useMemo(() => [
    ['Active Threats', threats.filter((item) => item.severity === 'critical' || item.severity === 'high').length],
    ['Threat Records', threats.length],
    ['Critical', threats.filter((item) => item.severity === 'critical').length],
    ['High Risk', threats.filter((item) => item.severity === 'high').length],
  ] as const, [threats]);

  const icons = [AlertTriangle, Network, ShieldAlert, Radio];

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Threat Intelligence</h1>
        <p className="text-sm text-[rgb(var(--text-muted))] mt-1">Flagged detections for {org}</p>
      </div>

      {loading ? (
        <div className="card h-32 flex items-center justify-center"><Loader2 className="w-5 h-5 animate-spin" /></div>
      ) : error ? (
        <div className="card border border-red-400/20 text-sm text-red-300">{error}</div>
      ) : (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {stats.map(([title, value], index) => {
              const Icon = icons[index];
              return (
                <div key={title} className="card">
                  <Icon className="w-5 h-5 text-violet-400 mb-3" />
                  <div className="text-2xl font-bold">{value}</div>
                  <div className="text-xs text-[rgb(var(--text-muted))] mt-1">{title}</div>
                </div>
              );
            })}
          </div>
          <section className="card">
            <h2 className="font-semibold mb-4">Threat Feed</h2>
            {threats.length ? (
              <div className="space-y-3">
                {threats.map((threat) => (
                  <div key={threat.analysis_id} className="rounded-lg p-4 border border-[rgb(var(--border-subtle))] bg-[var(--hover-bg)]">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className={`badge ${threat.severity === 'critical' || threat.severity === 'high' ? 'text-red-300 bg-red-400/10' : 'text-amber-300 bg-amber-400/10'}`}>
                          {threat.severity || 'unknown'}
                        </span>
                        <h3 className="font-semibold mt-2">
                          Risk score {threat.risk_score !== null ? Math.round(threat.risk_score) : 'N/A'} · {threat.risk_band || 'Unknown band'}
                        </h3>
                        <p className="text-xs text-[rgb(var(--text-muted))] mt-1">
                          {threat.recommended_action || 'No recommended action recorded.'}
                        </p>
                      </div>
                      <div className="text-xs text-[rgb(var(--text-muted))]">
                        {new Date(threat.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-[rgb(var(--text-muted))]">No flagged threats for this organization.</div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
