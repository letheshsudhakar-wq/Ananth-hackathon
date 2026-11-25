import React, { useEffect, useMemo, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { getDetectifHistory, getDetectifStats } from '@/services/api';
import type { DetectifHistoryItem, DetectifStats } from '@/services/api';

export function Analytics() {
  const [stats, setStats] = useState<DetectifStats | null>(null);
  const [items, setItems] = useState<DetectifHistoryItem[]>([]);
  const [range, setRange] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsResult, historyResult] = await Promise.all([
        getDetectifStats(),
        getDetectifHistory(200, 0)
      ]);
      setStats(statsResult);
      setItems(historyResult.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const periodItems = useMemo(() => {
    const cutoff = Date.now() - range * 24 * 60 * 60 * 1000;
    return items.filter((item) => new Date(item.created_at).getTime() >= cutoff);
  }, [items, range]);

  const chartData = useMemo(() => {
    const grouped = new Map<string, { date: string; genuine: number; synthetic: number }>();
    for (const item of periodItems) {
      const date = new Date(item.created_at).toLocaleDateString();
      const entry = grouped.get(date) ?? { date, genuine: 0, synthetic: 0 };
      if (item.is_synthetic) entry.synthetic += 1;
      else entry.genuine += 1;
      grouped.set(date, entry);
    }
    return Array.from(grouped.values()).reverse();
  }, [periodItems]);

  const genuineCount = periodItems.filter((item) => !item.is_synthetic).length;
  const syntheticCount = periodItems.filter((item) => item.is_synthetic).length;
  const periodTotal = periodItems.length;
  const syntheticPercentage = periodTotal
    ? (syntheticCount / periodTotal * 100).toFixed(1)
    : '0.0';
  const averageScore = periodItems.length
    ? periodItems.reduce((sum, item) => sum + item.score, 0) / periodItems.length
    : null;

  const metrics = [
    ['Total analyses', periodTotal],
    ['Genuine recordings', genuineCount],
    ['Synthetic recordings', syntheticCount],
    ['Synthetic rate', `${syntheticPercentage}%`],
    ['Average detection score', averageScore == null ? 'N/A' : `${(averageScore * 100).toFixed(2)}%`]
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="flex justify-between items-end gap-3">
        <div>
          <h1 className="text-xl font-semibold">Analytics</h1>
          <p className="text-sm text-[rgb(var(--text-muted))] mt-1">
            Calculated from saved Detectif analyses
          </p>
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map((days) => (
            <button
              key={days}
              onClick={() => setRange(days)}
              className={`btn btn-sm ${range === days ? 'btn-primary' : 'btn-outline'}`}
              aria-pressed={range === days}
            >
              {days} Days
            </button>
          ))}
          <button onClick={() => void load()} className="btn btn-outline btn-sm" disabled={loading}>
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="card p-4 text-sm text-red-400">{error}</div>}
      {loading && <div className="card p-5 text-sm">Loading database analytics...</div>}

      {!loading && stats && (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {metrics.map(([label, value]) => (
              <div key={label} className="card !p-4">
                <div className="text-xl font-bold">{value}</div>
                <div className="text-xs text-[rgb(var(--text-muted))] mt-1">{label}</div>
              </div>
            ))}
          </div>

          <section className="card">
            <h2 className="font-semibold mb-1">Daily analysis volume</h2>
            <p className="text-xs text-[rgb(var(--text-muted))] mb-4">
              Genuine and synthetic classifications in the latest 200 saved records
            </p>
            <div className="h-72">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid stroke="#243047" strokeDasharray="3 3" />
                    <XAxis dataKey="date" stroke="#64748b" />
                    <YAxis allowDecimals={false} stroke="#64748b" />
                    <Tooltip />
                    <Bar dataKey="genuine" name="Genuine" fill="#10b981" />
                    <Bar dataKey="synthetic" name="Synthetic" fill="#f43f5e" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-sm text-[rgb(var(--text-muted))]">
                  No saved analyses yet. Upload an audio recording to begin.
                </div>
              )}
            </div>
          </section>

          <p className="text-xs text-[rgb(var(--text-muted))]">
            Latest saved analysis: {stats.latest_analysis_at
              ? new Date(stats.latest_analysis_at).toLocaleString()
              : 'None'}
          </p>
        </>
      )}
    </div>
  );
}
