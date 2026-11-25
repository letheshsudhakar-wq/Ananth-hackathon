import React, { useEffect, useState } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Loader2 } from 'lucide-react';
import { getAnalytics } from '@/services/api';
import { useOrganization } from '@/context/OrganizationContext';
import type { AnalyticsResponse } from '@/types';

export function Analytics() {
  const [range,setRange]=useState(30);
  const { org } = useOrganization();
  const [data,setData]=useState<AnalyticsResponse|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);

  useEffect(() => {
    let cancelled=false;
    setLoading(true);
    setError(null);
    getAnalytics(range, org)
      .then((result)=>{ if(!cancelled) setData(result); })
      .catch((err)=>{ if(!cancelled) setError(err?.message || 'Could not load analytics.'); })
      .finally(()=>{ if(!cancelled) setLoading(false); });
    return () => { cancelled=true; };
  }, [range, org]);

  const trend=data?.trend ?? [];
  return <div className="max-w-6xl mx-auto space-y-5">
    <div className="flex items-end justify-between"><div><h1 className="text-xl font-semibold">Analytics</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Verification performance for {org}</p></div><div className="flex gap-2">{[7,30,90].map(days=><button key={days} onClick={()=>setRange(days)} className={`btn btn-sm ${range===days?'btn-primary':'btn-outline'}`} aria-pressed={range===days}>{days} Days</button>)}</div></div>
    {loading ? <div className="h-40 card flex items-center justify-center"><Loader2 className="w-5 h-5 animate-spin text-[rgb(var(--accent))]" /></div> :
      error ? <div className="card border border-red-400/20 text-red-300 text-sm">{error}</div> :
      <>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">{[
          ['Total',data?.total.toLocaleString() ?? '0'],
          ['Safe Rate',`${data?.safe_rate ?? 0}%`],
          ['Threat Rate',`${data?.threat_rate ?? 0}%`],
          ['Confidence',`${data?.confidence ?? 0}%`],
          ['Avg. Time',`${data?.average_time_seconds ?? 0}s`],
        ].map(([k,v])=><div key={k} className="card !p-4"><div className="text-xl font-bold">{v}</div><div className="text-xs text-[rgb(var(--text-muted))] mt-1">{k}</div></div>)}</div>
        <div className="grid lg:grid-cols-2 gap-5">
          <section className="card"><h2 className="font-semibold mb-4">Verification Trends</h2><div className="h-64">{trend.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={trend}><defs><linearGradient id="colorSafe" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.5}/><stop offset="95%" stopColor="#8b5cf7" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#243047" strokeDasharray="3 3"/><XAxis dataKey="day" stroke="#64748b"/><YAxis stroke="#64748b" allowDecimals={false}/><Tooltip/><Area type="monotone" dataKey="safe" stroke="#a78bfa" fill="url(#colorSafe)"/></AreaChart></ResponsiveContainer> : <div className="h-full flex items-center justify-center text-xs text-[rgb(var(--text-muted))]">No verification records in this period.</div>}</div></section>
          <section className="card"><h2 className="font-semibold mb-4">Safe vs Threat</h2><div className="h-64">{trend.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={trend}><CartesianGrid stroke="#243047" strokeDasharray="3 3"/><XAxis dataKey="day" stroke="#64748b"/><YAxis stroke="#64748b" allowDecimals={false}/><Tooltip/><Bar dataKey="safe" fill="#10b981" radius={4}/><Bar dataKey="threat" fill="#f43f5e" radius={4}/></BarChart></ResponsiveContainer> : <div className="h-full flex items-center justify-center text-xs text-[rgb(var(--text-muted))]">No verification records in this period.</div>}</div></section>
        </div>
      </>
    }
  </div>;
}
