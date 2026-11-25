import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, Mic, Link2, Trash2, Play, Square, RotateCcw } from 'lucide-react';

type Tab = 'upload' | 'record' | 'link';

export function VoiceVerification() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [recordedUrl, setRecordedUrl] = useState('');
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [recording]);

  const startRecording = async () => {
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      chunks.current = [];
      mediaRecorder.ondataavailable = (event) => event.data.size && chunks.current.push(event.data);
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' });
        setRecordedUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((track) => track.stop());
      };
      recorder.current = mediaRecorder;
      mediaRecorder.start();
      setSeconds(0);
      setRecording(true);
    } catch {
      setError('Microphone access was unavailable. You can still upload or link audio.');
    }
  };

  const stopRecording = () => {
    recorder.current?.stop();
    setRecording(false);
  };

  const verify = () => {
    if (tab === 'upload' && !file) return setError('Please upload an audio file.');
    if (tab === 'record' && !recordedUrl) return setError('Please record audio before verification.');
    if (tab === 'link') {
      try { if (!url) throw new Error(); new URL(url); } catch { return setError('Enter a valid audio URL.'); }
    }
    sessionStorage.setItem('ananth-verification-source', tab === 'upload' ? file?.name || 'Uploaded audio' : tab === 'record' ? 'Microphone recording' : url);
    navigate('/audio-intelligence');
  };

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div><h1 className="text-xl font-semibold">Voice Verification</h1><p className="text-sm text-[rgb(var(--text-muted))] mt-1">Upload, record or link an audio sample for demo analysis.</p></div>
      {error && <div className="rounded-lg border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      <div className="grid lg:grid-cols-[1fr_280px] gap-5">
        <section className="card">
          <div className="flex gap-2 border-b border-[rgb(var(--border-subtle))] pb-3">
            {([['upload', UploadCloud, 'Upload Audio'], ['record', Mic, 'Record Audio'], ['link', Link2, 'Audio Link']] as const).map(([value, Icon, label]) =>
              <button key={value} onClick={() => setTab(value)} className={`px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${tab === value ? 'bg-violet-600 text-white' : 'text-[rgb(var(--text-secondary))] hover:bg-[var(--hover-bg)]'}`}><Icon className="w-4 h-4" />{label}</button>)}
          </div>
          <div className="pt-5">
            {tab === 'upload' && (!file ? <label className="h-64 border border-dashed border-violet-400/30 rounded-xl flex flex-col items-center justify-center cursor-pointer bg-violet-500/5 hover:bg-violet-500/10">
              <UploadCloud className="w-10 h-10 text-violet-400 mb-3" /><strong>Drop audio here or browse</strong><span className="text-xs text-[rgb(var(--text-muted))] mt-2">MP3, WAV, M4A or OGG</span><input className="hidden" type="file" accept=".mp3,.wav,.m4a,.ogg,audio/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </label> : <div className="h-64 flex flex-col items-center justify-center rounded-xl bg-[var(--hover-bg)]"><audio controls src={URL.createObjectURL(file)} className="w-[80%]" /><p className="mt-4 text-sm">{file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB</p><button onClick={() => setFile(null)} className="btn btn-ghost mt-3"><Trash2 className="w-4 h-4" />Remove</button></div>)}
            {tab === 'record' && <div className="h-64 flex flex-col items-center justify-center rounded-xl border border-violet-400/20 bg-violet-500/5">
              <div className={`w-20 h-20 rounded-full flex items-center justify-center ${recording ? 'bg-red-500/25 text-red-300 animate-pulse' : 'bg-violet-500/20 text-violet-300'}`}><Mic className="w-9 h-9" /></div>
              <div className="font-mono text-lg mt-4">00:{seconds.toString().padStart(2, '0')}</div>
              <div className="flex gap-2 mt-4">{recording ? <button onClick={stopRecording} className="btn btn-danger"><Square className="w-4 h-4" />Stop</button> : <button onClick={startRecording} className="btn btn-primary"><Mic className="w-4 h-4" />Start Recording</button>}{recordedUrl && !recording && <><audio controls src={recordedUrl} /><button onClick={() => setRecordedUrl('')} className="btn btn-ghost"><RotateCcw className="w-4 h-4" /></button></>}</div>
            </div>}
            {tab === 'link' && <div className="h-64 flex flex-col items-center justify-center"><Link2 className="w-10 h-10 text-violet-400 mb-4" /><input className="input max-w-xl" placeholder="https://example.com/voice.mp3" value={url} onChange={(e) => setUrl(e.target.value)} /></div>}
          </div>
        </section>
        <aside className="card h-fit"><h2 className="font-semibold mb-4">Recording Details</h2><div className="space-y-3">{['Reference ID', 'Country', 'Language', 'Speaker ID (optional)'].map((label) => <label key={label} className="block text-xs text-[rgb(var(--text-muted))]">{label}<input className="input mt-1.5" placeholder={label.includes('Reference') ? 'REF-2026-001' : ''} /></label>)}</div></aside>
      </div>
      <button onClick={verify} className="btn btn-primary btn-lg w-full sm:w-auto"><Play className="w-4 h-4" />Verify Voice</button>
    </div>
  );
}
