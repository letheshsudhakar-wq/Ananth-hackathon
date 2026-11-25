import React from 'react';
import { AlertTriangle, Network, ShieldAlert, Radio } from 'lucide-react';

export function ThreatIntelligence() {
  const threats = [
    ['High','AI Voice Cloning','Synthetic executive call','Nov 25, 09:42','Active'],
    ['Medium','Replay Attack','Repeated customer authentication','Nov 24, 16:18','Monitoring'],
    ['High','Social Engineering','Urgent transfer request','Nov 24, 11:05','Active'],
  ];
  return <div className="max-w-6xl mx-auto space-y-5"><div><h1 className="text-xl font-semibold">Threat Intelligence</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Simulated cybersecurity intelligence feed</p></div>
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{[[AlertTriangle,'Active Threats','24'],[Network,'Threat Patterns','12'],[ShieldAlert,'High Risk','8'],[Radio,'Newly Detected','3']].map(([Icon,title,value]: any)=><div key={title} className="card"><Icon className="w-5 h-5 text-violet-400 mb-3" /><div className="text-2xl font-bold">{value}</div><div className="text-xs text-[rgb(var(--text-muted))] mt-1">{title}</div></div>)}</div>
    <div className="grid lg:grid-cols-[1fr_330px] gap-5"><section className="card"><h2 className="font-semibold mb-4">Threat Feed</h2><div className="space-y-3">{threats.map((t,i)=><div key={t[1]} className="rounded-lg p-4 border border-[rgb(var(--border-subtle))] bg-[var(--hover-bg)]"><div className="flex items-start justify-between gap-3"><div><span className={`badge ${t[0]==='High'?'text-red-300 bg-red-400/10':'text-amber-300 bg-amber-400/10'}`}>{t[0]}</span><h3 className="font-semibold mt-2">{t[1]}</h3><p className="text-xs text-[rgb(var(--text-muted))] mt-1">{t[2]}</p></div><div className="text-xs text-[rgb(var(--text-muted))]">{t[3]}</div></div></div>)}</div></section>
      <section className="card"><h2 className="font-semibold mb-4">Threat Map · Demo</h2><div className="h-72 rounded-xl relative overflow-hidden bg-[radial-gradient(circle_at_30%_45%,rgba(168,85,247,.28),transparent_8%),radial-gradient(circle_at_68%_38%,rgba(56,189,248,.25),transparent_8%),linear-gradient(145deg,#11182e,#080b18)]"><div className="absolute inset-0 opacity-25" style={{backgroundImage:'linear-gradient(rgba(148,163,184,.25) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,.25) 1px,transparent 1px)',backgroundSize:'28px 28px'}} />{[[28,40],[68,35],[55,68],[82,58],[42,76]].map(([x,y],i)=><span key={i} className="absolute w-3 h-3 rounded-full bg-cyan-300 shadow-[0_0_18px_#38bdf8]" style={{left:`${x}%`,top:`${y}%`}} />)}</div></section></div>
  </div>;
}
