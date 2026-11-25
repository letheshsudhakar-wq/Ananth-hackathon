import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, ArrowLeft, ArrowRight } from 'lucide-react';

export function AudioIntelligence() {
  const navigate = useNavigate();
  const source = sessionStorage.getItem('ananth-verification-source') || 'Demo audio';
  const bars = [32, 48, 70, 44, 82, 58, 35, 76, 92, 64, 46, 78, 54, 88, 42, 68, 82, 50, 72, 38];
  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div><h1 className="text-xl font-semibold">Audio Intelligence</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Demo quality assessment · {source}</p></div>
      <div className="grid lg:grid-cols-[260px_1fr] gap-5">
        <section className="card"><h2 className="font-semibold mb-5">Audio Quality</h2><div className="w-40 h-40 mx-auto rounded-full border-[12px] border-emerald-400/20 border-t-emerald-400 flex items-center justify-center"><div className="text-center"><strong className="text-3xl">94</strong><div className="text-xs text-emerald-300">Good</div></div></div>
          <div className="mt-6 space-y-3 text-sm">{[['Duration','12.4 sec'],['Noise','Low'],['Clipping','None'],['Sample Rate','48 kHz'],['Format','Audio demo']].map(([k,v]) => <div key={k} className="flex justify-between border-b border-[rgb(var(--border-subtle))] pb-2"><span className="text-[rgb(var(--text-muted))]">{k}</span><span>{v}</span></div>)}</div>
        </section>
        <section className="card"><h2 className="font-semibold mb-5">Waveform</h2><div className="h-56 flex items-center gap-1.5 rounded-xl px-4 bg-cyan-500/5 border border-cyan-400/10">{bars.map((h,i) => <span key={i} className="flex-1 rounded-full bg-gradient-to-t from-violet-600 to-cyan-300" style={{height:`${h}%`, opacity:.45+(i%4)*.12}} />)}</div></section>
      </div>
      <div className="card border border-emerald-400/20 flex flex-wrap items-center justify-between gap-4"><div className="flex items-center gap-3"><CheckCircle2 className="w-9 h-9 text-emerald-400" /><div><h2 className="font-semibold">Your audio is good to proceed.</h2><p className="text-xs text-[rgb(var(--text-muted))]">This is a simulated quality result, not a real AI judgment.</p></div></div><button onClick={() => navigate('/verification-progress')} className="btn btn-primary">Continue to Verification <ArrowRight className="w-4 h-4" /></button></div>
      <button onClick={() => navigate('/voice-verification')} className="btn btn-ghost"><ArrowLeft className="w-4 h-4" />Back</button>
    </div>
  );
}
