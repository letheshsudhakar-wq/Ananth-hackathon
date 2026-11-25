import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, CircleDashed } from 'lucide-react';

export function VerificationProgress() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timers = [600, 1500, 2400].map((time, index) => window.setTimeout(() => setStep(index + 1), time));
    const done = window.setTimeout(() => navigate('/verification-results'), 3300);
    return () => { timers.forEach(clearTimeout); clearTimeout(done); };
  }, [navigate]);
  const steps = ['Audio Assessment', 'AI Voice Analysis', 'Identity Verification'];
  return <div className="max-w-3xl mx-auto py-12"><div className="card text-center py-10"><div className="w-20 h-20 mx-auto rounded-full border-4 border-violet-500/20 border-t-violet-400 animate-spin" /><h1 className="text-2xl font-bold mt-6">Verification in Progress</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-2">Running simulated demo checks...</p><div className="mt-10 space-y-4 text-left">{steps.map((name,i) => <div key={name} className="flex items-center gap-3 p-3 rounded-lg bg-[var(--hover-bg)]">{step > i ? <CheckCircle2 className="text-emerald-400 w-5 h-5" /> : <CircleDashed className={`w-5 h-5 ${step === i ? 'text-violet-400 animate-pulse' : 'text-slate-600'}`} />}<span className="flex-1">{name}</span><span className="text-xs text-[rgb(var(--text-muted))]">{step > i ? 'Complete' : step === i ? 'Processing' : 'Waiting'}</span></div>)}</div></div></div>;
}
