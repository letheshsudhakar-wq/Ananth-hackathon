import React, { useEffect, useMemo, useState } from 'react';
import { Search, Eye, Loader2 } from 'lucide-react';
import { getAlerts } from '@/services/api';
import { useOrganization } from '@/context/OrganizationContext';
import { Modal } from '@/components/ui/Modal';
import type { AlertRecord } from '@/types';

export function DetectionHistory() {
  const { org }=useOrganization();
  const [records,setRecords]=useState<AlertRecord[]>([]);
  const [filter,setFilter]=useState('All');
  const [search,setSearch]=useState('');
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);
  const [selected,setSelected]=useState<AlertRecord|null>(null);
  useEffect(()=>{
    let cancelled=false; setLoading(true); setError(null);
    getAlerts({organization:org,limit:200}).then(res=>{if(!cancelled)setRecords(res.items)}).catch(err=>{if(!cancelled)setError(err?.message||'Could not load detection history.')}).finally(()=>{if(!cancelled)setLoading(false)});
    return()=>{cancelled=true};
  },[org]);
  const filtered=useMemo(()=>records.filter(r=>{
    const outcome=r.risk_score!==null&&r.risk_score>=50?'Threat':'Verified';
    return (filter==='All'||(filter==='Verified'&&outcome==='Verified')||(filter==='Suspicious'&&outcome==='Threat')) &&
      `${r.analysis_id} ${r.risk_band} ${r.severity} ${r.created_at}`.toLowerCase().includes(search.toLowerCase());
  }),[records,filter,search]);
  return <div className="max-w-6xl mx-auto space-y-5">
    <div><h1 className="text-xl font-semibold">Detection History</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Persisted analysis records</p></div>
    <div className="flex flex-wrap gap-3"><div className="relative flex-1 min-w-52"><Search className="absolute left-3 top-3 w-4 h-4 text-[rgb(var(--text-muted))]" /><input className="input pl-9" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search records..." /></div>{['All','Verified','Suspicious'].map(v=> <button key={v} onClick={()=>setFilter(v)} className={`btn btn-sm ${filter===v?'btn-primary':'btn-outline'}`}>{v}</button>)}</div>
    {loading?<div className="card h-40 flex items-center justify-center"><Loader2 className="w-5 h-5 animate-spin"/></div>:error?<div className="card border border-red-400/20 text-sm text-red-300">{error}</div>:<div className="card p-0 overflow-x-auto"><table className="w-full text-sm text-left"><thead className="text-xs text-[rgb(var(--text-muted))] border-b border-[rgb(var(--border-subtle))]"><tr>{['Reference','Date & Time','Risk Band','Result','Risk Score','Action'].map(h=><th key={h} className="px-4 py-3">{h}</th>)}</tr></thead><tbody>{filtered.map(r=>{const threat=r.risk_score!==null&&r.risk_score>=50;return<tr key={r.analysis_id} className="border-b border-[rgb(var(--border-subtle))] hover:bg-[var(--hover-bg)]"><td className="px-4 py-3 font-mono text-xs">{r.analysis_id.slice(0,12)}</td><td className="px-4 py-3">{new Date(r.created_at).toLocaleString()}</td><td className="px-4 py-3 capitalize">{r.risk_band||'Unknown'}</td><td className="px-4 py-3"><span className={`badge ${threat?'text-red-300 bg-red-400/10':'text-emerald-300 bg-emerald-400/10'}`}>{threat?'Suspicious':'Verified'}</span></td><td className="px-4 py-3">{r.risk_score!==null?Math.round(r.risk_score):'N/A'}</td><td className="px-4 py-3"><button className="btn btn-ghost btn-sm" onClick={()=>setSelected(r)}><Eye className="w-4 h-4"/>View</button></td></tr>})}{filtered.length===0&&<tr><td colSpan={6} className="px-4 py-8 text-center text-[rgb(var(--text-muted))]">No detection records match this view.</td></tr>}</tbody></table></div>}
    <Modal open={!!selected} onClose={()=>setSelected(null)} title="Detection Details" footer={<button className="btn btn-primary" onClick={()=>setSelected(null)}>Close</button>}>{selected&&<div className="space-y-3 text-sm"><div className="flex justify-between"><span className="text-[rgb(var(--text-muted))]">Analysis ID</span><span className="font-mono">{selected.analysis_id}</span></div><div className="flex justify-between"><span className="text-[rgb(var(--text-muted))]">Created</span><span>{new Date(selected.created_at).toLocaleString()}</span></div><div className="flex justify-between"><span className="text-[rgb(var(--text-muted))]">Risk score</span><span>{selected.risk_score!==null?Math.round(selected.risk_score):'N/A'}</span></div><div className="flex justify-between"><span className="text-[rgb(var(--text-muted))]">Severity</span><span className="capitalize">{selected.severity||'N/A'}</span></div><div><span className="text-[rgb(var(--text-muted))]">Recommended action</span><p className="mt-1">{selected.recommended_action||'No action recorded.'}</p></div></div>}</Modal>
  </div>;
}
