import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, AlertTriangle, ArrowLeft, ArrowRight } from 'lucide-react';
import type { AnalysisResponse } from '@/types';

export function AudioIntelligence() {
  const navigate = useNavigate();
  const source = sessionStorage.getItem('ananth-verification-source') || 'No source';
  const raw = sessionStorage.getItem('ananth-verification-result');
  const result = raw ? JSON.parse(raw) as AnalysisResponse : null;
  const risk = result?.risk_score ?? 0;
  const safe = !result?.flagged && risk < 50;
  const bars = [32, 48, 70, 44, 82, 58, 35, 76, 92, 64, 46, 78, 54, 88, 42, 68, 82, 50, 72, 38];

  if (!result) {
    return (
      <div className="max-w-3xl mx-auto card space-y-4">
        <h1 className="text-xl font-semibold">Audio Intelligence</h1>
        <p className="text-sm text-[rgb(var(--text-muted))]">No verification result is available. Run a real analysis first.</p>
        <button className="btn btn-primary" onClick={() => navigate('/voice-verification')}>Return to Voice Verification</button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Audio Intelligence</h1>
        <p className="text-sm text-[rgb(var(--text-muted))] mt-1">Backend analysis result · {source}</p>
      </div>
      <div className="grid lg:grid-cols-[260px_1fr] gap-5">
        <section className="card">
          <h2 className="font-semibold mb-5">Risk Summary</h2>
          <div className={`w-40 h-40 mx-auto rounded-full border-[12px] flex items-center justify-center ${safe ? 'border-emerald-400/20 border-t-emerald-400' : 'border-red-400/20 border-t-red-400'}`}>
            <div className="text-center">
              <strong className="text-3xl">{Math.round(risk)}</strong>
              <div className={`text-xs ${safe ? 'text-emerald-300' : 'text-red-300'}`}>{safe ? 'Lower Risk' : 'Higher Risk'}</div>
            </div>
          </div>
          <div className="mt-6 space-y-3 text-sm">
            {[
              ['Risk band', result.band || 'Unknown'],
              ['Severity', result.severity || 'Unknown'],
              ['Confidence', result.confidence !== null ? `${Math.round(result.confidence * 100)}%` : 'N/A'],
              ['Latency', result.processing_latency_ms !== null ? `${Math.round(result.processing_latency_ms)} ms` : 'N/A'],
              ['Analysis ID', result.analysis_id.slice(0, 12)],
            ].map(([key, value]) => (
              <div key={key} className="flex justify-between gap-3 border-b border-[rgb(var(--border-subtle))] pb-2">
                <span className="text-[rgb(var(--text-muted))]">{key}</span><span className="text-right capitalize">{value}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="card">
          <h2 className="font-semibold mb-5">Signal Snapshot</h2>
          <div className="h-56 flex items-center gap-1.5 rounded-xl px-4 bg-cyan-500/5 border border-cyan-400/10">
            {bars.map((height, index) => (
              <span key={index} className="flex-1 rounded-full bg-gradient-to-t from-violet-600 to-cyan-300" style={{ height: `${height}%`, opacity: 0.45 + (index % 4) * 0.12 }} />
            ))}
          </div>
        </section>
      </div>
      <div className={`card flex flex-wrap items-center justify-between gap-4 ${safe ? 'border border-emerald-400/20' : 'border border-red-400/20'}`}>
        <div className="flex items-center gap-3">
          {safe ? <CheckCircle2 className="w-9 h-9 text-emerald-400" /> : <AlertTriangle className="w-9 h-9 text-red-400" />}
          <div>
            <h2 className="font-semibold">{safe ? 'The analysis indicates lower risk.' : 'The analysis indicates elevated risk.'}</h2>
            <p className="text-xs text-[rgb(var(--text-muted))]">{result.recommended_action || 'Review the analysis result.'}</p>
          </div>
        </div>
        <button onClick={() => navigate('/verification-progress')} className="btn btn-primary">View Verification <ArrowRight className="w-4 h-4" /></button>
      </div>
      <button onClick={() => navigate('/voice-verification')} className="btn btn-ghost"><ArrowLeft className="w-4 h-4" />Back</button>
    </div>
  );
}
