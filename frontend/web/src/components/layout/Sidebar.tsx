/**
 * src/components/layout/Sidebar.tsx — Navigation rail
 *
 * Wider 64px (w-16) icon rail with generous touch targets and spacing.
 */
import React from 'react';
import { NavLink } from 'react-router-dom';
import { Tooltip } from '@/components/ui/Tooltip';
import { FileLock2, AudioWaveform, Radio, ShieldAlert, ScrollText, Settings, LayoutDashboard, Users, BrainCircuit, BarChart3, Activity } from 'lucide-react';

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  accent: string;
}

const navItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, accent: 'rgb(var(--accent))' },
  { to: '/voice-verification', label: 'Voice Verification', icon: AudioWaveform, accent: 'rgb(var(--accent))' },
  { to: '/audio-intelligence', label: 'Audio Intelligence', icon: BrainCircuit, accent: 'rgb(var(--accent-soft))' },
  { to: '/enrolled-speakers', label: 'Enrolled Speakers', icon: Users, accent: 'rgb(var(--risk-low))' },
  { to: '/detection-history', label: 'Detection History', icon: ScrollText, accent: 'rgb(var(--risk-medium))' },
  { to: '/threat-intelligence', label: 'Threat Intelligence', icon: ShieldAlert, accent: 'rgb(var(--risk-critical))' },
  { to: '/analytics', label: 'Analytics', icon: BarChart3, accent: 'rgb(var(--cyan))' },
  { to: '/settings', label: 'Settings', icon: Settings, accent: 'rgb(var(--accent-soft))' },
];

export function Sidebar() {
  return (
    <aside className="flex w-16 shrink-0 flex-col items-center select-none max-md:fixed max-md:bottom-0 max-md:left-0 max-md:right-0 max-md:z-40 max-md:w-full max-md:h-16 max-md:flex-row max-md:border-t max-md:border-[rgb(var(--border-subtle))] max-md:bg-[rgb(var(--rail-bg))]">
      {/* Nav icons with generous spacing and comfortable targets */}
      <nav className="flex flex-col items-center gap-3 pt-10 flex-1 w-full max-md:flex-row max-md:justify-around max-md:overflow-x-auto max-md:pt-0 max-md:px-1 max-md:gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
<NavLink
              key={item.to}
              to={item.to}
              className="relative w-full flex justify-center"
            >
              {({ isActive }) => (
                <Tooltip label={item.label} side="right">
                  <span
                    className={`flex items-center justify-center w-11 h-11 rounded-xl transition-colors duration-150 ${
                      isActive
                        ? 'text-[rgb(var(--accent))]'
                        : 'text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-secondary))] hover:bg-[var(--hover-bg)]'
                    }`}
                    style={isActive ? { color: item.accent } : undefined}
                  >
                    {/* Active indicator — left edge bar */}
                    {isActive && (
                      <span
                        className="absolute left-1 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-full"
                        style={{ background: item.accent }}
                      />
                    )}
                    <Icon className="w-5 h-5" strokeWidth={isActive ? 2.2 : 1.8} />
                  </span>
                </Tooltip>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom: privacy policy link */}
      <div className="pb-3 flex justify-center w-full">
<NavLink
          to="/privacy"
          className="relative w-full flex justify-center"
        >
          {({ isActive }) => (
            <Tooltip label="Privacy Policy & Compliance" side="right">
              <span
                className={`flex items-center justify-center w-11 h-11 rounded-xl transition-colors duration-150 ${
                  isActive
                    ? 'text-[rgb(var(--accent))]'
                    : 'text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-secondary))] hover:bg-[var(--hover-bg)]'
                }`}
              >
                {isActive && (
                  <span className="absolute left-1 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-full bg-[rgb(var(--accent))]" />
                )}
                <FileLock2 className="w-5 h-5" strokeWidth={isActive ? 2.2 : 1.8} />
              </span>
            </Tooltip>
          )}
        </NavLink>
      </div>
    </aside>
  );
}
