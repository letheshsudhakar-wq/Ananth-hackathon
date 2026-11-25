import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, AudioLines, TriangleAlert, CircleDashed, Bell, Activity, Database, Server } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const chartData = [
  { day: 'Mon', value: 64 }, { day: 'Tue', value: 48 }, { day: 'Wed', value: 58 },
  { day: 'Thu', value: 68 }, { day: 'Fri', value: 52 }, { day: 'Sat', value: 48 },
  { day: 'Sun', value: 72 },
];
const stats = [
  { title: 'Total Verifications', value: '12,480', change: '+12.5%', icon: AudioLines, color: 'text-cyan-300', bg: 'bg-cyan-400/10' },
  { title: 'Verified Voices', value: '12,232', change: '+8.2%', icon: ShieldCheck, color: 'text-emerald-300', bg: 'bg-emerald-400/10' },
  { title: 'Suspicious Recordings', value: '248', change: '-4.2%', icon: TriangleAlert, color: 'text-red-300', bg: 'bg-red-400/10' },
  { title: 'Inconclusive', value: '96', change: '+1.8%', icon: CircleDashed, color: 'text-amber-300', bg: 'bg-amber-400/10' },
];

export function Dashboard() {
  const [range, setRange] = useState('7 Days');
  const activity = [
    ['Safe Recording','Nov 25, 2026 · 09:45 AM','Voice verified','safe'],
    ['Suspicious Voice Detected','Nov 25, 2026 · 08:32 AM','Pattern anomaly','threat'],
    ['Verification Completed','Nov 25, 2026 · 07:15 AM','Identity confirmed','safe'],
    ['Inconclusive Analysis','Nov 24, 2026 · 11:28 PM','Manual review required','warning'],
  ];
  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-2xl font-bold">Good Morning, Ruchi</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Monitor and manage voice authentication activity.</p></div>
        <Link to="/voice-verification" className="btn btn-primary">Start Verification</Link>
      </div>
      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {stats.map(({title,value,change,icon:Icon,color,bg}) => <section key={title} className="card !p-4"><div className="flex items-start justify-between"><div><div className="text-xs text-[rgb(var(--text-muted))]">{title}</div><div className="text-2xl font-bold mt-2">{value}</div></div><div className={`w-9 h-9 rounded-lg ${bg} ${color} flex items-center justify-center`}><Icon className="w-5 h-5"/></div></div><div className="mt-3 text-xs text-emerald-300">{change} <span className="text-[rgb(var(--text-muted))]">vs last period</span></div></section>)}
      </div>
      <div className="grid xl:grid-cols-[1.6fr_1fr] gap-4">
        <section className="card"><div className="flex items-center justify-between"><div><h2 className="font-semibold">Detection Overview</h2><p className="text-xs text-[rgb(var(--text-muted))]">Verification activity</p></div><div className="flex gap-1">{['7 Days','30 Days','90 Days'].map(v=><button key={v} onClick={()=>setRange(v)} className={`px-2 py-1 rounded text-xs ${range===v?'bg-violet-600 text-white':'text-[rgb(var(--text-muted))] hover:bg-[var(--hover-bg)]'}`}>{v}</button>)}</div></div>
          <div className="h-64 mt-4"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}><defs><linearGradient id="dashGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#a855f7" stopOpacity={0.55}/><stop offset="95%" stopColor="#a855f7" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#253047" strokeDasharray="3 3"/><XAxis dataKey="day" stroke="#64748b"/><YAxis stroke="#64748b"/><Tooltip/><Area type="monotone" dataKey="value" stroke="#c084fc" strokeWidth={2} fill="url(#dashGradient)"/></AreaChart></ResponsiveContainer></div>
        </section>
        <section className="card"><div className="flex items-center justify-between"><h2 className="font-semibold">Recent Activity</h2><Link to="/detection-history" className="text-xs text-violet-300">View All</Link></div>
          <div className="mt-4 space-y-2">{activity.map(([title,time,desc,type])=><div key={title} className="flex items-center gap-3 p-2.5 rounded-lg bg-[var(--hover-bg)]"><div className={`w-8 h-8 rounded-lg flex items-center justify-center ${type==='threat'?'bg-red-400/10 text-red-300':type==='warning'?'bg-amber-400/10 text-amber-300':'bg-emerald-400/10 text-emerald-300'}`}><Bell className="w-4 h-4"/></div><div className="min-w-0 flex-1"><div className="text-xs font-medium truncate">{title}</div><div className="text-[10px] text-[rgb(var(--text-muted))]">{time}</div></div><span className="text-[10px] text-[rgb(var(--text-secondary))]">{desc}</span></div>)}</div>
        </section>
      </div>
      <div className="grid xl:grid-cols-[1.6fr_1fr] gap-4">
        <section className="card"><div className="flex items-center justify-between"><h2 className="font-semibold">Detection History</h2><Link to="/detection-history" className="text-xs text-violet-300">View All</Link></div><div className="overflow-x-auto mt-4"><table className="w-full text-xs text-left"><thead className="text-[rgb(var(--text-muted))]"><tr>{['Reference','Date & Time','Type','Decision','Confidence','Action'].map(h=><th key={h} className="py-2 px-2">{h}</th>)}</tr></thead><tbody>{[['AN-1201','Nov 25, 10:32','Upload','Safe','98.7%','Safe'],['AN-1198','Nov 25, 09:15','Upload','Threat','82.4%','Review']].map(r=><tr key={r[0]} className="border-t border-[rgb(var(--border-subtle))]">{r.map((v,i)=><td key={i} className="py-3 px-2">{i===3?<span className={v==='Safe'?'text-emerald-300':'text-red-300'}>{v}</span>:v}</td>)}</tr>)}</tbody></table></div></section>
        <section className="card"><h2 className="font-semibold">System Status</h2><div className="mt-4 space-y-3">{[[Activity,'AI Engine','Active'],[Server,'Audio Processing','Online'],[Server,'Backend Server','Online'],[Database,'Database','Healthy']].map(([Icon,title,status]:any)=><div key={title} className="flex items-center justify-between text-sm"><div className="flex items-center gap-2 text-[rgb(var(--text-secondary))]"><Icon className="w-4 h-4"/>{title}</div><span className="flex items-center gap-1.5 text-xs text-emerald-300"><span className="w-2 h-2 rounded-full bg-emerald-400"/>{status}</span></div>)}</div><div className="mt-5 p-3 rounded-lg border border-cyan-400/15 bg-cyan-400/5"><div className="flex items-center gap-2 text-cyan-300 font-semibold text-sm"><ShieldCheck className="w-4 h-4"/>System Secure</div><p className="text-xs text-[rgb(var(--text-muted))] mt-1">Last scan: 2 minutes ago · 0 threats detected</p></div></section>
      </div>
    </div>
  );
}
