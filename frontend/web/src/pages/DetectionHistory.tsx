import React, { useEffect, useMemo, useState } from 'react';
import { Search, RefreshCw } from 'lucide-react';
import { getDetectifHistory } from '@/services/api';
import type { DetectifHistoryItem } from '@/services/api';

export function DetectionHistory() {
  const [items, setItems] = useState<DetectifHistoryItem[]>([]);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getDetectifHistory(200, 0);
      setItems(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load analysis history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadHistory(); }, []);

  const filtered = useMemo(() => items.filter((item) => {
    const matchesFilter =
      filter === 'all' || item.label === filter;
    const text = [
      item.analysis_id, item.filename, item.label,
      item.request_id ?? '', item.operation_id ?? ''
    ].join(' ').toLowerCase();
    return matchesFilter && text.includes(search.toLowerCase());
  }), [items, filter, search]);

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="flex flex-wrap justify-between items-end gap-3">
        <div>
          <h1 className="text-xl font-semibold">Detection History</h1>
          <p className="text-sm text-[rgb(var(--text-muted))] mt-1">
            Saved audio analyses from the database
          </p>
        </div>
        <button onClick={() => void loadHistory()} className="btn btn-outline btn-sm" disabled={loading}>
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-52">
          <Search className="absolute left-3 top-3 w-4 h-4 text-[rgb(var(--text-muted))]" />
          <input className="input pl-9" value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search filename or analysis ID..." />
        </div>
        {['all', 'genuine', 'synthetic'].map(value => (
          <button key={value} onClick={() => setFilter(value)}
            className={`btn btn-sm ${filter === value ? 'btn-primary' : 'btn-outline'}`}>
            {value === 'all' ? 'All' : value === 'genuine' ? 'Genuine' : 'Synthetic'}
          </button>
        ))}
      </div>

      {error && <div className="card p-4 text-sm text-red-400">{error}</div>}
      {loading && <div className="card p-6 text-sm">Loading saved analyses...</div>}

      {!loading && !error && (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-[rgb(var(--text-muted))] border-b border-[rgb(var(--border-subtle))]">
              <tr>
                {['Analysis ID', 'Date & Time', 'Audio file', 'Result', 'Detection score', 'Duration'].map(h =>
                  <th key={h} className="px-4 py-3">{h}</th>
                )}
              </tr>
            </thead>
            <tbody>
              {filtered.map(item => (
                <tr key={item.analysis_id} className="border-b border-[rgb(var(--border-subtle))]">
                  <td className="px-4 py-3 font-mono text-xs" title={item.analysis_id}>
                    {item.analysis_id.slice(0, 8)}...
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 max-w-52 truncate" title={item.filename}>{item.filename}</td>
                  <td className="px-4 py-3">
                    <span className={`badge ${item.is_synthetic ? 'text-red-300 bg-red-400/10' : 'text-emerald-300 bg-emerald-400/10'}`}>
                      {item.is_synthetic ? 'Synthetic' : 'Genuine'}
                    </span>
                  </td>
                  <td className="px-4 py-3">{(item.score * 100).toFixed(2)}%</td>
                  <td className="px-4 py-3">{item.duration_seconds.toFixed(2)}s</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-[rgb(var(--text-muted))]">
                  No saved analyses match this search.
                </td></tr>
              )}
            </tbody>
          </table>
          <div className="px-4 py-3 text-xs text-[rgb(var(--text-muted))]">
            Showing {filtered.length} of {items.length} loaded records (maximum 200)
          </div>
        </div>
      )}
    </div>
  );
}
