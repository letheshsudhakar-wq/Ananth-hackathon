/**
 * src/pages/VoiceVerification.tsx  (Phase 4 — real backend wiring)
 * Collects audio (upload / record), runs full ANANTH orchestration,
 * and shows live agent activity inline before navigating to results.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud, Mic, Square, RotateCcw, Trash2, Play, Loader2, Globe2,
} from 'lucide-react';
import { useOrchestration } from '@/hooks/useOrchestration';
import { AgentActivityPanel } from '@/components/agents/AgentActivityPanel';
import { RecoveryPanel } from '@/components/agents/RecoveryPanel';

type Tab = 'upload' | 'record';

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi' },
  { value: 'ta', label: 'Tamil' },
  { value: 'kn', label: 'Kannada' },
  { value: 'te', label: 'Telugu' },
  { value: 'gu', label: 'Gujarati' },
];

export function VoiceVerification() {
  const navigate = useNavigate();
  const { phase, result, recovery, agentStates, error, run, reset } = useOrchestration();

  const [tab, setTab] = useState<Tab>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState('en');
  const [localError, setLocalError] = useState('');

  // Recording state
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState('');
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    if (!recording) return;
    const t = window.setInterval(() => setSeconds((v) => v + 1), 1000);
    return () => clearInterval(t);
  }, [recording]);

  // Navigate to results when done
  useEffect(() => {
    if (phase === 'done' && result) {
      sessionStorage.setItem('ananth-orch-result', JSON.stringify(result));
      if (recovery) sessionStorage.setItem('ananth-recovery', JSON.stringify(recovery));
      // Short delay so user sees agent panel complete
      const t = setTimeout(() => navigate('/verification-results'), 1200);
      return () => clearTimeout(t);
    }
  }, [phase, result, recovery, navigate]);

  const startRecording = async () => {
    setLocalError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      });
      chunks.current = [];
      mr.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunks.current, { type: mr.mimeType });
        setRecordedBlob(blob);
        setRecordedUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((t) => t.stop());
      };
      recorder.current = mr;
      mr.start();
      setSeconds(0);
      setRecording(true);
    } catch {
      setLocalError('Microphone access denied. Please upload a file instead.');
    }
  };

  const stopRecording = () => {
    recorder.current?.stop();
    setRecording(false);
  };

  const handleVerify = useCallback(async () => {
    setLocalError('');
    let blob: Blob | null = null;

    if (tab === 'upload') {
      if (!file) return setLocalError('Please upload an audio file.');
      blob = file;
    } else {
      if (!recordedBlob) return setLocalError('Please record audio first.');
      blob = recordedBlob;
    }

    await run(blob, { language, useGemini: false });
  }, [tab, file, recordedBlob, language, run]);

  const handleReset = () => {
    reset();
    setFile(null);
    setRecordedBlob(null);
    setRecordedUrl('');
    setSeconds(0);
    setLocalError('');
  };

  const isRunning = phase === 'uploading' || phase === 'processing';
  const isDone = phase === 'done';

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Voice Verification</h1>
        <p className="text-sm text-[rgb(var(--text-muted))] mt-1">
          Upload or record an audio sample for multi-agent authentication.
        </p>
      </div>

      {(localError || error) && (
        <div className="rounded-lg border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-300">
          {localError || error}
        </div>
      )}

      <div className="grid lg:grid-cols-[1fr_320px] gap-5">
        {/* Left: audio input */}
        <section className="card">
          <div className="flex gap-2 border-b border-[rgb(var(--border-subtle))] pb-3 mb-5">
            {(['upload', 'record'] as Tab[]).map((t) => (
              <button
                key={t}
                disabled={isRunning || isDone}
                onClick={() => setTab(t)}
                className={`px-4 py-2 rounded-lg text-sm flex items-center gap-2 disabled:opacity-50 ${
                  tab === t
                    ? 'bg-violet-600 text-white'
                    : 'text-[rgb(var(--text-secondary))] hover:bg-[var(--hover-bg)]'
                }`}
              >
                {t === 'upload' ? <UploadCloud className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                {t === 'upload' ? 'Upload Audio' : 'Record Audio'}
              </button>
            ))}
          </div>

          {/* Upload tab */}
          {tab === 'upload' && (
            !file ? (
              <label className="h-56 border border-dashed border-violet-400/30 rounded-xl flex flex-col items-center justify-center cursor-pointer bg-violet-500/5 hover:bg-violet-500/10 transition-colors">
                <UploadCloud className="w-10 h-10 text-violet-400 mb-3" />
                <strong className="text-sm">Drop audio here or browse</strong>
                <span className="text-xs text-[rgb(var(--text-muted))] mt-2">WAV, MP3, M4A, OGG, WebM</span>
                <input
                  className="hidden"
                  type="file"
                  accept=".mp3,.wav,.m4a,.ogg,.webm,audio/*"
                  onChange={(e) => { setFile(e.target.files?.[0] ?? null); setLocalError(''); }}
                />
              </label>
            ) : (
              <div className="h-56 flex flex-col items-center justify-center rounded-xl bg-[var(--hover-bg)] gap-3">
                <audio controls src={URL.createObjectURL(file)} className="w-[80%]" />
                <p className="text-sm">{file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB</p>
                {!isRunning && !isDone && (
                  <button onClick={() => setFile(null)} className="btn btn-ghost btn-sm">
                    <Trash2 className="w-4 h-4" /> Remove
                  </button>
                )}
              </div>
            )
          )}

          {/* Record tab */}
          {tab === 'record' && (
            <div className="h-56 flex flex-col items-center justify-center rounded-xl border border-violet-400/20 bg-violet-500/5 gap-4">
              <div className={`w-20 h-20 rounded-full flex items-center justify-center ${
                recording ? 'bg-red-500/25 text-red-300 animate-pulse' : 'bg-violet-500/20 text-violet-300'
              }`}>
                <Mic className="w-9 h-9" />
              </div>
              <div className="font-mono text-lg">00:{seconds.toString().padStart(2, '0')}</div>
              <div className="flex items-center gap-2">
                {recording ? (
                  <button onClick={stopRecording} className="btn btn-danger btn-sm">
                    <Square className="w-4 h-4" /> Stop
                  </button>
                ) : (
                  <button onClick={startRecording} disabled={isRunning || isDone} className="btn btn-primary btn-sm">
                    <Mic className="w-4 h-4" /> Start Recording
                  </button>
                )}
                {recordedUrl && !recording && (
                  <>
                    <audio controls src={recordedUrl} className="h-8" />
                    {!isRunning && !isDone && (
                      <button onClick={() => { setRecordedBlob(null); setRecordedUrl(''); }} className="btn btn-ghost btn-sm">
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {/* Language + verify */}
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-[rgb(var(--text-secondary))]">
              <Globe2 className="w-4 h-4" />
              <select
                value={language}
                disabled={isRunning || isDone}
                onChange={(e) => setLanguage(e.target.value)}
                className="input h-8 text-sm py-0 pr-7"
              >
                {LANGUAGE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </label>

            {!isDone && (
              <button
                onClick={handleVerify}
                disabled={isRunning || (!file && !recordedBlob)}
                className="btn btn-primary"
              >
                {isRunning ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> {phase === 'uploading' ? 'Uploading…' : 'Verifying…'}</>
                ) : (
                  <><Play className="w-4 h-4" /> Verify Voice</>
                )}
              </button>
            )}

            {(phase === 'done' || phase === 'error') && (
              <button onClick={handleReset} className="btn btn-ghost">
                <RotateCcw className="w-4 h-4" /> New Session
              </button>
            )}
          </div>
        </section>

        {/* Right: live agent panel */}
        <aside className="space-y-4">
          <AgentActivityPanel
            phase={phase}
            agentStates={agentStates}
            processingTimeMs={result?.processing_time_ms}
            simulationMode={result?.simulation_mode}
            activatedCount={result?.activated_agents?.length}
          />

          {phase === 'done' && result && (
            <RecoveryPanel
              outcome={result.outcome}
              recoveryAction={result.recovery_action}
              customerMessage={recovery?.customer_message ?? result.customer_message}
              geminiUsed={recovery?.gemini_used}
              onRetry={handleReset}
              onRecordAgain={() => { handleReset(); setTab('record'); }}
            />
          )}
        </aside>
      </div>
    </div>
  );
}
