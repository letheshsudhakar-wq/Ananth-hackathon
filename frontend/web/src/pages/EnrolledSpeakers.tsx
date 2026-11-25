import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Trash2, UserRound, Loader2 } from 'lucide-react';
import { deleteSpeaker, listSpeakers } from '@/services/api';
import type { SpeakerProfile } from '@/types';

export function EnrolledSpeakers() {
  const [speakers,setSpeakers]=useState<SpeakerProfile[]>([]);
  const [search,setSearch]=useState('');
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);

  const load=()=>{
    setLoading(true); setError(null);
    listSpeakers().then(setSpeakers).catch((err)=>setError(err?.message||'Could not load enrolled speakers.')).finally(()=>setLoading(false));
  };
  useEffect(load,[]);
  const filtered=useMemo(()=>speakers.filter(s=>`${s.speaker_id} ${s.display_name}`.toLowerCase().includes(search.toLowerCase())),[speakers,search]);
  const remove=async(speaker:SpeakerProfile)=>{
    if(!window.confirm(`Delete enrolled speaker "${speaker.display_name}"?`)) return;
    try { await deleteSpeaker(speaker.speaker_id); setSpeakers(v=>v.filter(s=>s.speaker_id!==speaker.speaker_id)); }
    catch(err:any){ setError(err?.message||'Could not delete speaker.'); }
  };

  return <div className="max-w-6xl mx-auto space-y-5">
    <div className="flex items-end justify-between"><div><h1 className="text-xl font-semibold">Enrolled Speakers</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Manage registered speaker identities</p></div><Link to="/voiceprints" className="btn btn-primary"><Plus className="w-4 h-4" />Enroll Speaker</Link></div>
    <div className="relative max-w-sm"><Search className="absolute left-3 top-3 w-4 h-4 text-[rgb(var(--text-muted))]" /><input className="input pl-9" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search speakers..." /></div>
    {loading ? <div className="card h-40 flex items-center justify-center"><Loader2 className="w-5 h-5 animate-spin" /></div> :
      error ? <div className="card border border-red-400/20 text-sm text-red-300">{error}</div> :
      filtered.length===0 ? <div className="card text-sm text-[rgb(var(--text-muted))]">No enrolled speakers found.</div> :
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">{filtered.map(s=><div key={s.speaker_id} className="card"><div className="flex justify-between"><div className="w-12 h-12 rounded-xl bg-violet-500/15 flex items-center justify-center"><UserRound className="w-6 h-6 text-violet-300"/></div><button className="btn btn-ghost btn-sm text-red-300" onClick={()=>remove(s)} aria-label={`Delete ${s.display_name}`}><Trash2 className="w-4 h-4"/></button></div><h2 className="font-semibold mt-4">{s.display_name}</h2><p className="text-xs text-[rgb(var(--text-muted))] mt-1 font-mono">{s.speaker_id}</p><div className="mt-4 text-xs border-t border-[rgb(var(--border-subtle))] pt-3 text-[rgb(var(--text-muted))]">Updated {new Date(s.updated_at).toLocaleString()}</div></div>)}</div>}
  </div>;
}
