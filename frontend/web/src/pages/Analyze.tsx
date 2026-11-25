
import { useState, type ChangeEvent } from 'react';
import {
  FileAudio,
  CheckCircle2,
  RotateCcw,
  ShieldCheck,
  ShieldAlert,
  Clock3,
} from 'lucide-react';

import {
  analyzeWithDetectif,
  type DetectifResponse,
} from '@/services/api';

export function Analyze() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DetectifResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    if (selected.size > 25 * 1024 * 1024) {
      setError('File exceeds the 25 MB upload limit.');
      return;
    }

    setFile(selected);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const response = await analyzeWithDetectif(file);
      setResult(response);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : 'Audio analysis failed.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      <div>
        <h1 className="text-lg font-semibold text-[rgb(var(--text-primary))]">
          Analyze Audio
        </h1>
        <p className="text-xs text-[rgb(var(--text-muted))] mt-0.5">
          Analyze voice recordings for potentially AI-generated speech
        </p>
      </div>

      {!result && (
        <div className="card p-8 flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-xl bg-[rgb(var(--accent))] text-white flex items-center justify-center mb-5">
            <FileAudio size={24} />
          </div>

          <h3 className="text-sm font-semibold text-[rgb(var(--text-primary))] mb-1">
            Upload Call Recording
          </h3>

          <p className="text-xs text-[rgb(var(--text-muted))] max-w-xs mb-6">
            Upload a speech recording for Aletheia deepfake analysis.
            Maximum file size: 25 MB.
          </p>

          <input
            type="file"
            id="audio-upload"
            accept="*/*"
            onChange={handleFileChange}
            className="hidden"
          />

          {file ? (
            <div className="p-3 rounded-md border border-[rgb(var(--border-subtle))] flex items-center gap-3 w-full max-w-sm">
              <FileAudio className="w-4 h-4 shrink-0" />
              <div className="flex-1 min-w-0 text-left">
                <span className="text-xs font-medium block truncate">
                  {file.name}
                </span>
                <span className="text-[10px]">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB
                </span>
              </div>
              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="btn btn-primary btn-sm shrink-0"
              >
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          ) : (
            <label
              htmlFor="audio-upload"
              className="btn btn-primary cursor-pointer"
            >
              Select Audio File
            </label>
          )}

          {loading && (
            <p className="text-xs mt-5 text-[rgb(var(--text-muted))]">
              Analyzing audio with Aletheia. This may take a few minutes...
            </p>
          )}

          {error && (
            <div className="mt-5 text-sm text-red-500">
              {error}
              <button
                onClick={handleAnalyze}
                className="underline ml-2"
                disabled={!file || loading}
              >
                Retry
              </button>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="card p-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <div>
                <span className="text-xs font-medium block">
                  Analysis Complete
                </span>
                <span className="text-[10px] text-[rgb(var(--text-muted))]">
                  Request: {result.request_id}
                </span>
              </div>
            </div>
            <button onClick={handleReset} className="btn btn-ghost btn-sm">
              <RotateCcw size={13} /> New Analysis
            </button>
          </div>

          <div className="card p-6 text-center">
            {result.result.is_synthetic ? (
              <ShieldAlert className="w-12 h-12 text-red-500 mx-auto mb-3" />
            ) : (
              <ShieldCheck className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
            )}

            <p className="text-xs text-[rgb(var(--text-muted))] uppercase">
              Aletheia Detection Result
            </p>
            <h2 className={`text-2xl font-bold mt-2 ${
              result.result.is_synthetic ? 'text-red-500' : 'text-emerald-500'
            }`}>
              {result.result.is_synthetic
                ? 'AI-GENERATED AUDIO'
                : 'GENUINE AUDIO'}
            </h2>
            <p className="text-xs text-[rgb(var(--text-muted))] mt-2">
              Provider classification: {result.result.label}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card p-5">
              <p className="text-xs text-[rgb(var(--text-muted))]">
                Detection score
              </p>
              <p className="text-2xl font-bold mt-2">
                {(result.result.score * 100).toFixed(2)}%
              </p>
            </div>

            <div className="card p-5">
              <p className="text-xs text-[rgb(var(--text-muted))]">
                Detection threshold
              </p>
              <p className="text-2xl font-bold mt-2">
                {(result.result.threshold * 100).toFixed(2)}%
              </p>
            </div>

            <div className="card p-5">
              <p className="text-xs text-[rgb(var(--text-muted))]">
                Audio duration
              </p>
              <p className="text-2xl font-bold mt-2">
                {result.result.duration_seconds.toFixed(2)}s
              </p>
            </div>
          </div>

          <div className="card p-5 space-y-3 text-xs">
            <h3 className="text-sm font-semibold">Analysis Details</h3>
            {result.analysis_id && (
              <div className="flex justify-between gap-4">
                <span>Saved Analysis ID</span>
                <span className="truncate ml-4">{result.analysis_id}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span>Classification</span>
              <span>{result.result.label}</span>
            </div>
            <div className="flex justify-between">
              <span>Synthetic audio</span>
              <span>{String(result.result.is_synthetic)}</span>
            </div>
            <div className="flex justify-between">
              <span>Scored duration</span>
              <span>{result.result.scored_seconds.toFixed(2)} seconds</span>
            </div>
            <div className="flex justify-between">
              <span>Operation ID</span>
              <span className="truncate ml-4">{result.operation_id}</span>
            </div>
          </div>

          <p className="text-[10px] text-[rgb(var(--text-muted))] flex items-center gap-1">
            <Clock3 size={12} />
            Request ID: {result.request_id}
          </p>
          <p className="text-xs text-[rgb(var(--text-muted))]">
            Automated detection is a signal, not proof of authenticity.
            Do not use this result alone to authorize sensitive actions.
          </p>
        </div>
      )}
    </div>
  );
}

