/**
 * src/pages/VerificationProgress.tsx  (Phase 4 — real pipeline progress)
 * Lightweight redirect page that forwards completed sessions to results.
 */
import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

export function VerificationProgress() {
  const navigate = useNavigate();

  useEffect(() => {
    // If the orchestration result is already in session (from VoiceVerification),
    // go directly to results. Otherwise redirect to voice-verification to start fresh.
    const result = sessionStorage.getItem('ananth-orch-result')
      || sessionStorage.getItem('ananth-verification-result');
    const t = setTimeout(() => {
      navigate(result ? '/verification-results' : '/voice-verification', { replace: true });
    }, 500);
    return () => clearTimeout(t);
  }, [navigate]);

  return (
    <div className="max-w-3xl mx-auto py-12">
      <div className="card text-center py-10">
        <Loader2 className="w-12 h-12 mx-auto text-violet-400 animate-spin" />
        <h1 className="text-xl font-bold mt-6">Verification in Progress</h1>
        <p className="text-sm text-[rgb(var(--text-muted))] mt-2">
          Running ANANTH multi-agent pipeline…
        </p>
      </div>
    </div>
  );
}
