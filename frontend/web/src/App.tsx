/**
 * src/App.tsx
 * Top-level application routing and context providers.
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { OrganizationProvider } from '@/context/OrganizationContext';
import { AlertProvider } from '@/context/AlertContext';
import { SignalSettingsProvider } from '@/context/SignalSettingsContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { AppShell } from '@/components/layout/AppShell';

import { Dashboard } from '@/pages/Dashboard';
import { LiveCall } from '@/pages/LiveCall';
import { Analyze } from '@/pages/Analyze';
import { Voiceprints } from '@/pages/Voiceprints';
import { Alerts } from '@/pages/Alerts';
import { Audit } from '@/pages/Audit';
import { Settings } from '@/pages/Settings';
import { Privacy } from '@/pages/Privacy';
import { NotFound } from '@/pages/NotFound';
import { LandingPage } from '@/pages/LandingPage';
import { VoiceVerification } from '@/pages/VoiceVerification';
import { AudioIntelligence } from '@/pages/AudioIntelligence';
import { VerificationProgress } from '@/pages/VerificationProgress';
import { VerificationResults } from '@/pages/VerificationResults';
import { DetectionHistory } from '@/pages/DetectionHistory';
import { ThreatIntelligence } from '@/pages/ThreatIntelligence';
import { Analytics } from '@/pages/Analytics';
import { EnrolledSpeakers } from '@/pages/EnrolledSpeakers';
import { Profile } from '@/pages/Profile';

export function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <OrganizationProvider>
          <SignalSettingsProvider>
            <AlertProvider>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route element={<AppShell />}>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/voice-verification" element={<VoiceVerification />} />
                  <Route path="/audio-intelligence" element={<AudioIntelligence />} />
                  <Route path="/verification-progress" element={<VerificationProgress />} />
                  <Route path="/verification-results" element={<VerificationResults />} />
                  <Route path="/detection-history" element={<DetectionHistory />} />
                  <Route path="/threat-intelligence" element={<ThreatIntelligence />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/enrolled-speakers" element={<EnrolledSpeakers />} />
                  <Route path="/live-call" element={<LiveCall />} />
                  <Route path="/analyze" element={<Analyze />} />
                  <Route path="/voiceprints" element={<Voiceprints />} />
                  <Route path="/alerts" element={<Alerts />} />
                  <Route path="/audit" element={<Audit />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/profile" element={<Profile />} />
                  <Route path="/privacy" element={<Privacy />} />
                </Route>
                <Route path="*" element={<NotFound />} />
              </Routes>
            </AlertProvider>
          </SignalSettingsProvider>
        </OrganizationProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
