import React, { useMemo, useState } from 'react';
import { Search, Eye } from 'lucide-react';

const records = [
  ['AN-2026-1201','Nov 25, 2026 10:32','mobile-recording.wav','Verified','98.7%','Mark safe'],
  ['AN-2026-1198','Nov 25, 2026 09:15','incoming-call.mp3','Suspicious','82.4%','Review'],
  ['AN-2026-1194','Nov 24, 2026 18:42','customer-voice.m4a','Verified','96.1%','Mark safe'],
  ['AN-2026-1189','Nov 24, 2026 14:08','unknown-audio.ogg','Inconclusive','61.3%','Recheck'],
];

export function DetectionHistory() {
  const [filter,setFilter]=useState('All'); const [search,setSearch]=useState('');
  const filtered=useMemo(()=>records.filter(r=> (filter==='All'||r[3]===filter)&&r.join(' ').toLowerCase().includes(search.toLowerCase()) ),[filter,search]);
  return <div className="max-w-6xl mx-auto space-y-5"><div><h1 className="text-xl font-semibold">Detection History</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Searchable demo verification records</p></div>
    <div className="flex flex-wrap gap-3"><div className="relative flex-1 min-w-52"><Search className="absolute left-3 top-3 w-4 h-4 text-[rgb(var(--text-muted))]" /><input className="input pl-9" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search records..." /></div>{['All','Verified','Suspicious','Inconclusive'].map(v=> <button key={v} onClick={()=>setFilter(v)} className={`btn btn-sm ${filter===v?'btn-primary':'btn-outline'}`}>{v}</button>)}</div>
    <div className="card p-0 overflow-x-auto"><table className="w-full text-sm text-left"><thead className="text-xs text-[rgb(var(--text-muted))] border-b border-[rgb(var(--border-subtle))]"><tr>{['Reference','Date & Time','Caller / File','Result','Confidence','Action'].map(h=><th key={h} className="px-4 py-3">{h}</th>)}</tr></thead><tbody>{filtered.map(r=><tr key={r[0]} className="border-b border-[rgb(var(--border-subtle))] hover:bg-[var(--hover-bg)]">{r.slice(0,5).map((v,i)=>i===3?<td key={i} className="px-4 py-3"><span className={`badge ${v==='Verified'?'text-emerald-300 bg-emerald-400/10':v==='Suspicious'?'text-red-300 bg-red-400/10':'text-amber-300 bg-amber-400/10'}`}>{v}</span></td>:<td key={i} className="px-4 py-3">{v}</td>)}<td className="px-4 py-3"><button className="btn btn-ghost btn-sm"><Eye className="w-4 h-4" />View</button></td></tr>)}</tbody></table></div>
  </div>;
}
