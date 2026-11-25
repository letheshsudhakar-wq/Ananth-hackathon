import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, Download, History, RotateCcw, LayoutDashboard } from 'lucide-react';

export function VerificationResults() {
  const navigate = useNavigate();
  const download = () => {
    const blob = new Blob(['ANANTH Demo Verification Report\nResult: Verified / Safe\nConfidence: 98.7%\nDemo insight only — no real AI determination.\n'], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'ananth-demo-report.txt'; anchor.click(); URL.revokeObjectURL(url);
  };
  return <div className="max-w-6xl mx-auto space-y-5">
    <div><h1 className="text-xl font-semibold">Verification Results</h1><p className="text-xs text-amber-300 mt-1">Simulated demo result</p></div>
    <div className="grid lg:grid-cols-[320px_1fr] gap-5">
      <section className="card flex flex-col items-center text-center py-8 border border-emerald-400/20"><ShieldCheck className="w-16 h-16 text-emerald-400" /><h2 className="text-2xl font-bold mt-4 text-emerald-300">Verified / Safe</h2><div className="mt-5 w-32 h-32 rounded-full border-[10px] border-emerald-400/20 border-t-emerald-400 flex items-center justify-center"><strong className="text-3xl">98.7%</strong></div><span className="mt-4 badge text-emerald-300 bg-emerald-400/10">Low Risk</span></section>
      <section className="card"><h2 className="font-semibold mb-4">Demo Analysis Insights</h2><div className="grid sm:grid-cols-2 gap-3">{[['Voice consistency','High'],['Audio quality','Good'],['Suspicious patterns','Not detected'],['Signal anomalies','None']].map(([k,v]) => <div key={k} className="rounded-lg p-4 bg-[var(--hover-bg)]"><div className="text-xs text-[rgb(var(--text-muted))]">{k}</div><div className="font-semibold mt-1">{v}</div></div>)}</div><div className="mt-5 text-xs text-[rgb(var(--text-muted))] border-t border-[rgb(var(--border-subtle))] pt-4">These insights are fictional frontend demonstration data.</div></section>
    </div>
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3"><button onClick={download} className="btn btn-primary"><Download className="w-4 h-4" />Download Report</button><Link to="/detection-history" className="btn btn-outline"><History className="w-4 h-4" />View History</Link><button onClick={() => navigate('/voice-verification')} className="btn btn-outline"><RotateCcw className="w-4 h-4" />Scan Another File</button><Link to="/dashboard" className="btn btn-ghost"><LayoutDashboard className="w-4 h-4" />Back to Dashboard</Link></div>
  </div>;
}
