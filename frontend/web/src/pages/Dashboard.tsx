import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useHealthCheck } from '@/hooks/useHealthCheck';
import { getDetectifStats } from '@/services/api';
import type { DetectifStats } from '@/services/api';
import {
  AudioWaveform,
  ScrollText,
  BarChart3,
  Settings,
  CheckCircle2,
  XCircle,
  RefreshCw,
} from 'lucide-react';

export function Dashboard() {
  const { health, error, lastChecked, refresh } = useHealthCheck();
  const [stats, setStats] = useState<DetectifStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  const loadStats = async () => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      const data = await getDetectifStats();
      setStats(data);
    } catch (err) {
      setStatsError(err instanceof Error ? err.message : 'Could not load analysis statistics.');
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    void loadStats();
  }, []);

  const online = health?.status === 'ok';

  const tools = [
    {
      to: '/analyze',
      title: 'Analyze Audio',
      description: 'Upload an audio recording for external Aletheia deepfake analysis.',
      cta: 'Analyze a recording',
      icon: AudioWaveform,
    },
    {
      to: '/detection-history',
      title: 'Detection History',
      description: 'View previously analyzed recordings and their saved results.',
      cta: 'View analysis records',
      icon: ScrollText,
    },
    {
      to: '/analytics',
      title: 'Analytics',
      description: 'Review genuine and synthetic classifications and detection statistics.',
      cta: 'View analytics',
      icon: BarChart3,
    },
  ];

  const metricCards = [
    { label: 'Total analyses', value: stats?.total ?? 0 },
    { label: 'Genuine recordings', value: stats?.genuine_count ?? 0 },
    { label: 'Synthetic recordings', value: stats?.synthetic_count ?? 0 },
    {
      label: 'Synthetic rate',
      value: `${(stats?.synthetic_percentage ?? 0).toFixed(1)}%`,
    },
  ];

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[rgb(var(--text-primary))]">
            ANANTH Dashboard
          </h1>
          <p className="text-xs text-[rgb(var(--text-muted))] mt-1">
            Audio deepfake analysis workspace
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => { void loadStats(); void refresh(); }} className="btn btn-ghost btn-sm">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <Link to="/settings" className="btn btn-ghost btn-sm">
            <Settings className="w-3.5 h-3.5" /> Settings
          </Link>
        </div>
      </div>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-[rgb(var(--text-primary))]">
            Saved analysis statistics
          </h2>
          {statsLoading && (
            <span className="text-xs text-[rgb(var(--text-muted))]">Loading...</span>
          )}
        </div>

        {statsError && (
          <p className="text-xs text-red-500 mb-3">{statsError}</p>
        )}

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {metricCards.map((metric) => (
            <div key={metric.label} className="card !p-4">
              <p className="text-[11px] text-[rgb(var(--text-muted))]">{metric.label}</p>
              <p className="text-2xl font-semibold mt-2 text-[rgb(var(--text-primary))]">
                {statsLoading ? '—' : metric.value}
              </p>
            </div>
          ))}
        </div>

        <p className="text-[10px] text-[rgb(var(--text-muted))] mt-2">
          Statistics are retrieved from saved Detectif analysis records in the backend database.
        </p>
      </section>

      <section>
        <h2 className="text-sm font-semibold text-[rgb(var(--text-primary))] mb-3">
          Analysis workspace
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {tools.map((tool) => {
            const Icon = tool.icon;
            return (
              <Link
                key={tool.to}
                to={tool.to}
                className="group card !p-5 flex flex-col hover:border-[rgb(var(--accent))/0.5] hover:shadow-md transition-all"
              >
                <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-3 text-white shadow-md bg-[rgb(var(--accent))] group-hover:scale-105 transition-transform">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-semibold text-[rgb(var(--text-primary))]">
                  {tool.title}
                </h3>
                <p className="text-[11px] text-[rgb(var(--text-muted))] leading-relaxed mt-1 flex-1">
                  {tool.description}
                </p>
                <span className="text-[11px] font-medium mt-3 text-[rgb(var(--accent))]">
                  {tool.cta} ?
                </span>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="card !p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-[rgb(var(--text-primary))]">
            Backend status
          </h2>
          {online ? (
            <span className="flex items-center gap-1 text-[11px] font-mono text-[rgb(var(--status-online))]">
              <CheckCircle2 className="w-3.5 h-3.5" /> ONLINE
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] font-mono text-[rgb(var(--status-offline))]">
              <XCircle className="w-3.5 h-3.5" /> {error ? 'OFFLINE' : 'CHECKING'}
            </span>
          )}
        </div>

        <div className="space-y-2">
          {[
            ['API', online ? 'Online' : error ? 'Unreachable' : 'Checking'],
            ['ML service', health?.ml_service ?? 'Not reported'],
            ['Database', health?.database ?? 'Not reported'],
            ['Backend version', health?.version ?? 'Not reported'],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between py-1 border-b border-[rgb(var(--border-subtle))] last:border-0">
              <span className="text-[11px] text-[rgb(var(--text-secondary))]">{label}</span>
              <span className="text-[11px] font-mono text-[rgb(var(--text-primary))]">{value}</span>
            </div>
          ))}
        </div>

        <p className="text-[9px] font-mono text-[rgb(var(--text-muted))] mt-3">
          {lastChecked ? `Last checked ${new Date(lastChecked).toLocaleTimeString()}` : 'Waiting for health check'}
        </p>
      </section>

      <p className="text-[10px] text-[rgb(var(--text-muted))]">
        Current integration performs analysis after an audio file is uploaded. It does not provide live-call monitoring.
      </p>
    </div>
  );
}
