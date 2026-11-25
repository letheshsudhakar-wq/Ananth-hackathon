import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, Download, History, RotateCcw, LayoutDashboard } from 'lucide-react';
import type { AnalysisResponse } from '@/types';

export function VerificationResults() {
  const navigate = useNavigate();
  const raw = sessionStorage.getItem('ananth-verification-result');
  const result = raw ? JSON.parse(raw) as AnalysisResponse : null;
  const download = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify({
      application: 'Ananth',
      source: sessionStorage.getItem('ananth-verification-source'),
      details: JSON.parse(sessionStorage.getItem('ananth-verification-details') || '{}'),
      analysis: result,
    }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `ananth-analysis-${result.analysis_id}.json`; anchor.click(); URL.revokeObjectURL(url);
  };
  if (!result) {
    return <div className="max-w-3xl mx-auto card space-y-4"><h1 className="text-xl font-semibold">Verification Results</h1><p className="text-sm text-[rgb(var(--text-muted))]">No verification result is available.</p><button className="btn btn-primary" onClick={()=>navigate('/voice-verification')}>Start Verification</button></div>;
  }
  const risk = result.risk_score ?? 0;
  const safe = !result.flagged && risk < 50;
  return <div className="max-w-6xl mx-auto space-y-5">
    <div><h1 className="text-xl font-semibold">Verification Results</h1><p className="text-xs text-[rgb(var(--text-muted))] mt-1">Persisted backend analysis</p></div>
    <div className="grid lg:grid-cols-[320px_1fr] gap-5">
      <section className={`card flex flex-col items-center text-center py-8 ${safe ? 'border border-emerald-400/20' : 'border border-red-400/20'}`}>
        {safe ? <ShieldCheck className="w-16 h-16 text-emerald-400" /> : <ShieldAlert className="w-16 h-16 text-red-400" />}
        <h2 className={`text-2xl font-bold mt-4 ${safe ? 'text-emerald-300' : 'text-red-300'}`}>{safe ? 'Verified / Safe' : 'Suspicious / Threat'}</h2>
        <div className={`mt-5 w-32 h-32 rounded-full border-[10px] flex items-center justify-center ${safe ? 'border-emerald-400/20 border-t-emerald-400' : 'border-red-400/20 border-t-red-400'}`}><strong className="text-3xl">{Math.round(risk)}</strong></div>
        <span className={`mt-4 badge ${safe ? 'text-emerald-300 bg-emerald-400/10' : 'text-red-300 bg-red-400/10'}`}>{result.band || result.severity || 'Unknown'} Risk</span>
      </section>
      <section className="card">
        <h2 className="font-semibold mb-4">Analysis Insights</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {[
            ['Confidence', result.confidence !== null ? `${Math.round(result.confidence * 100)}%` : 'N/A'],
            ['Organization', result.organization || 'Unknown'],
            ['Processing time', result.processing_latency_ms !== null ? `${Math.round(result.processing_latency_ms)} ms` : 'N/A'],
            ['Analysis ID', result.analysis_id],
          ].map(([key,value]) => (
            <div key={key} className="rounded-lg p-4 bg-[var(--hover-bg)]">
              <div className="text-xs text-[rgb(var(--text-muted))]">{key}</div>
              <div className="font-semibold mt-1 break-all">{value}</div>
            </div>
          ))}
        </div>
        <div className="mt-5 text-xs text-[rgb(var(--text-muted))] border-t border-[rgb(var(--border-subtle))] pt-4">
          {result.recommended_action || 'No recommended action was returned.'}
        </div>
      </section>
    </div>
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3"><button onClick={download} className="btn btn-primary"><Download className="w-4 h-4" />Download Report</button><Link to="/detection-history" className="btn btn-outline"><History className="w-4 h-4" />View History</Link><button onClick={() => navigate('/voice-verification')} className="btn btn-outline"><RotateCcw className="w-4 h-4" />Scan Another File</button><Link to="/dashboard" className="btn btn-ghost"><LayoutDashboard className="w-4 h-4" />Back to Dashboard</Link></div>
  </div>;
}
