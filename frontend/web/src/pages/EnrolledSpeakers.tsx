import React, { useState } from 'react';
import { Plus, Search, MoreHorizontal, UserRound } from 'lucide-react';

export function EnrolledSpeakers() {
  const [open,setOpen]=useState(false); const [speakers,setSpeakers]=useState([
    ['SPK-1001','Ruchi Sharma','Nov 12, 2026','English','Active','248'],
    ['SPK-1002','Aarav Patel','Nov 08, 2026','Hindi','Active','184'],
    ['SPK-1003','Maya Rao','Oct 29, 2026','English','Inactive','52'],
  ]);
  const [name,setName]=useState('');
  const add=(e:React.FormEvent)=>{e.preventDefault(); if(!name.trim())return; setSpeakers(v=>[['SPK-'+(1004+v.length),name.trim(),'Nov 25, 2026','English','Active','0'],...v]); setName('');setOpen(false)};
  return <div className="max-w-6xl mx-auto space-y-5"><div className="flex items-end justify-between"><div><h1 className="text-xl font-semibold">Enrolled Speakers</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Manage registered speaker identities</p></div><button onClick={()=>setOpen(true)} className="btn btn-primary"><Plus className="w-4 h-4" />Add Speaker</button></div>
    <div className="relative max-w-sm"><Search className="absolute left-3 top-3 w-4 h-4 text-[rgb(var(--text-muted))]" /><input className="input pl-9" placeholder="Search speakers..." /></div>
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">{speakers.map(s=><div key={s[0]} className="card"><div className="flex justify-between"><div className="w-12 h-12 rounded-xl bg-violet-500/15 flex items-center justify-center"><UserRound className="w-6 h-6 text-violet-300"/></div><button className="btn btn-ghost btn-sm" onClick={()=>{if(confirm('Delete this speaker?'))setSpeakers(v=>v.filter(x=>x[0]!==s[0]))}}><MoreHorizontal className="w-4 h-4"/></button></div><h2 className="font-semibold mt-4">{s[1]}</h2><p className="text-xs text-[rgb(var(--text-muted))]">{s[0]} · {s[3]}</p><div className="mt-4 flex justify-between text-xs border-t border-[rgb(var(--border-subtle))] pt-3"><span className="text-[rgb(var(--text-muted))]">{s[5]} verifications</span><span className={s[4]==='Active'?'text-emerald-300':'text-slate-400'}>{s[4]}</span></div></div>)}</div>
    {open&&<div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onMouseDown={()=>setOpen(false)}><form onSubmit={add} onMouseDown={e=>e.stopPropagation()} className="card w-full max-w-md"><h2 className="font-semibold mb-4">Add Speaker</h2><label className="block text-xs text-[rgb(var(--text-muted))]">Name<input className="input mt-1.5" value={name} onChange={e=>setName(e.target.value)} /></label><div className="flex justify-end gap-2 mt-5"><button type="button" onClick={()=>setOpen(false)} className="btn btn-outline">Cancel</button><button className="btn btn-primary">Enroll Speaker</button></div></form></div>}
  </div>;
}
