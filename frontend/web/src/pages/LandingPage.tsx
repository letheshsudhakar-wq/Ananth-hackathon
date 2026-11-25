import React from 'react';
import { Link } from 'react-router-dom';
import { Mic, ShieldCheck, AudioLines, ScanLine, Globe2, LockKeyhole, ArrowRight } from 'lucide-react';

const features = [
  [Mic, 'AI Voice Detection', 'Identify cloned, altered and synthetic speech.'],
  [ScanLine, 'Real-Time Verification', 'Analyze voice confidence in a guided workflow.'],
  [AudioLines, 'Audio Intelligence', 'Review quality, noise, clipping and format signals.'],
  [ShieldCheck, 'Speaker Authentication', 'Compare recordings with trusted speaker profiles.'],
  [Globe2, 'Threat Intelligence', 'Review persisted patterns from flagged voice detections.'],
  [LockKeyhole, 'Secure Processing', 'Raw recordings are discarded after analysis.'],
] as const;

export function LandingPage() {
  return (
    <main className="min-h-screen overflow-hidden text-white" style={{ background: 'radial-gradient(circle at 78% 20%, rgba(37,99,235,.22), transparent 28%), radial-gradient(circle at 20% 70%, rgba(124,58,237,.16), transparent 30%), #050816' }}>
      <nav className="h-20 max-w-7xl mx-auto px-6 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 font-bold tracking-[0.16em]">
          <span className="w-10 h-10 rounded-xl border border-cyan-400/30 bg-cyan-400/10 flex items-center justify-center"><AudioLines className="w-5 h-5 text-cyan-300" /></span>
          ANANTH
        </Link>
        <div className="hidden md:flex items-center gap-8 text-sm text-slate-300">
          <a href="#features" className="hover:text-white">Features</a>
          <a href="#how" className="hover:text-white">How It Works</a>
          <a href="#about" className="hover:text-white">About</a>
        </div>
        <Link to="/dashboard" className="px-5 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-sm font-semibold shadow-[0_0_24px_rgba(124,58,237,.35)]">Get Started</Link>
      </nav>

      <section className="max-w-7xl mx-auto px-6 min-h-[520px] grid md:grid-cols-2 items-center">
        <div className="relative z-10 py-16">
          <div className="inline-flex items-center gap-2 text-xs text-cyan-300 mb-6 px-3 py-1.5 rounded-full border border-cyan-400/20 bg-cyan-400/5"><ShieldCheck className="w-4 h-4" /> AI-Powered Security</div>
          <h1 className="text-5xl sm:text-6xl font-black leading-[1.02] tracking-tight">Voice Fraud<br /><span className="text-cyan-300">Detection</span></h1>
          <p className="mt-6 max-w-xl text-slate-300 text-lg leading-relaxed">Detect, verify and stay secure. AI-powered voice authentication designed to identify suspicious, cloned and manipulated audio.</p>
          <div className="mt-8 flex gap-3">
            <Link to="/voice-verification" className="px-6 py-3 rounded-lg bg-violet-600 hover:bg-violet-500 font-semibold flex items-center gap-2 shadow-[0_12px_40px_rgba(124,58,237,.28)]">Start Analysis <ArrowRight className="w-4 h-4" /></Link>
            <a href="#how" className="px-6 py-3 rounded-lg border border-slate-600/70 bg-slate-900/40 font-semibold hover:border-violet-400">Learn More</a>
          </div>
        </div>

        <div className="relative h-[420px] hidden md:flex items-center justify-center">
          <div className="absolute w-72 h-72 rounded-full border border-violet-400/20 shadow-[0_0_80px_rgba(37,99,235,.22)]" />
          <div className="absolute w-56 h-56 rounded-full border border-cyan-400/20 animate-pulse" />
          <div className="relative w-36 h-36 rounded-[42%] border-2 border-cyan-300/50 bg-gradient-to-b from-violet-500/35 to-cyan-400/10 flex items-center justify-center shadow-[0_0_50px_rgba(56,189,248,.25)]">
            <Mic className="w-16 h-16 text-slate-100" />
          </div>
          {[0, 1, 2, 3, 4].map((n) => <span key={n} className="absolute w-2 h-2 rounded-full bg-cyan-300/80" style={{ left: `${18 + n * 16}%`, top: `${40 + (n % 2) * 12}%`, boxShadow: '0 0 12px #38bdf8' }} />)}
        </div>
      </section>

      <section id="features" className="max-w-7xl mx-auto px-6 pb-20">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map(([Icon, title, description]) => (
            <div key={title} className="rounded-2xl border border-violet-400/10 bg-slate-900/50 p-5 hover:-translate-y-1 transition-transform">
              <Icon className="w-7 h-7 text-cyan-300 mb-4" />
              <h3 className="font-bold">{title}</h3>
              <p className="text-sm text-slate-400 mt-2">{description}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="how" className="border-y border-slate-800/70 bg-slate-950/40">
        <div className="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-8">
          {['Upload or record audio', 'Run backend verification', 'Review the analysis report'].map((step, i) => (
            <div key={step} className="flex gap-4"><span className="w-9 h-9 rounded-full bg-violet-600/30 border border-violet-400/40 flex items-center justify-center text-violet-300 font-bold">{i + 1}</span><div><h3 className="font-semibold">{step}</h3><p className="text-sm text-slate-400 mt-1">{['Provide a voice sample.', 'The backend processes the audio with the configured ML service.', 'Explore the persisted risk and recommendation result.'][i]}</p></div></div>
          ))}
        </div>
      </section>
    </main>
  );
}
