import React, { useState } from 'react';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  {day:'Mon',safe:78,threat:12,activity:90},{day:'Tue',safe:84,threat:9,activity:93},{day:'Wed',safe:72,threat:18,activity:90},{day:'Thu',safe:88,threat:7,activity:95},{day:'Fri',safe:92,threat:11,activity:103},{day:'Sat',safe:76,threat:14,activity:90},{day:'Sun',safe:96,threat:6,activity:102}
];
export function Analytics() {
  const [range,setRange]=useState('30 Days');
  return <div className="max-w-6xl mx-auto space-y-5"><div className="flex items-end justify-between"><div><h1 className="text-xl font-semibold">Analytics</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Simulated verification performance</p></div><div className="flex gap-2">{['7 Days','30 Days','90 Days'].map(v=><button key={v} onClick={()=>setRange(v)} className={`btn btn-sm ${range===v?'btn-primary':'btn-outline'}`}>{v}</button>)}</div></div>
    <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">{[['Total','12,480'],['Safe Rate','98.7%'],['Threat Rate','1.3%'],['Confidence','96.2%'],['Avg. Time','1.8s']].map(([k,v])=><div key={k} className="card !p-4"><div className="text-xl font-bold">{v}</div><div className="text-xs text-[rgb(var(--text-muted))] mt-1">{k}</div></div>)}</div>
    <div className="grid lg:grid-cols-2 gap-5"><section className="card"><h2 className="font-semibold mb-4">Verification Trends</h2><div className="h-64"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><defs><linearGradient id="colorSafe" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.5}/><stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#243047" strokeDasharray="3 3"/><XAxis dataKey="day" stroke="#64748b"/><YAxis stroke="#64748b"/><Tooltip/><Area type="monotone" dataKey="safe" stroke="#a78bfa" fill="url(#colorSafe)"/></AreaChart></ResponsiveContainer></div></section>
      <section className="card"><h2 className="font-semibold mb-4">Safe vs Threat</h2><div className="h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={data}><CartesianGrid stroke="#243047" strokeDasharray="3 3"/><XAxis dataKey="day" stroke="#64748b"/><YAxis stroke="#64748b"/><Tooltip/><Bar dataKey="safe" fill="#10b981" radius={4}/><Bar dataKey="threat" fill="#f43f5e" radius={4}/></BarChart></ResponsiveContainer></div></section></div>
  </div>;
}
