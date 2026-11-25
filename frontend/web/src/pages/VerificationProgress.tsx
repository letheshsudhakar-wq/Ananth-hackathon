import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export function VerificationProgress() {
  const navigate = useNavigate();
  useEffect(() => {
    const done = window.setTimeout(() => navigate('/verification-results'), 700);
    return () => { clearTimeout(done); };
  }, [navigate]);
  return <div className="max-w-3xl mx-auto py-12"><div className="card text-center py-10"><div className="w-20 h-20 mx-auto rounded-full border-4 border-violet-500/20 border-t-violet-400 animate-spin" /><h1 className="text-2xl font-bold mt-6">Finalizing Verification</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-2">Preparing the persisted backend analysis report...</p></div></div>;
}
