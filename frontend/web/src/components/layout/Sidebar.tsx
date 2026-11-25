import React from 'react';
import { NavLink } from 'react-router-dom';
import { Tooltip } from '@/components/ui/Tooltip';
import {
  LayoutDashboard,
  AudioWaveform,
  ScrollText,
  BarChart3,
  Settings,
  FileLock2,
} from 'lucide-react';

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  accent: string;
}

const navItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, accent: 'rgb(var(--accent))' },
  { to: '/analyze', label: 'Analyze Audio', icon: AudioWaveform, accent: 'rgb(var(--accent))' },
  { to: '/detection-history', label: 'Detection History', icon: ScrollText, accent: 'rgb(var(--risk-medium))' },
  { to: '/analytics', label: 'Analytics', icon: BarChart3, accent: 'rgb(var(--cyan))' },
  { to: '/settings', label: 'Settings', icon: Settings, accent: 'rgb(var(--accent-soft))' },
];

export function Sidebar() {
  return (
    <aside className="flex w-16 shrink-0 flex-col items-center select-none max-md:fixed max-md:bottom-0 max-md:left-0 max-md:right-0 max-md:z-40 max-md:w-full max-md:h-16 max-md:flex-row max-md:border-t max-md:border-[rgb(var(--border-subtle))] max-md:bg-[rgb(var(--rail-bg))]">
      <nav className="flex flex-col items-center gap-3 pt-10 flex-1 w-full max-md:flex-row max-md:justify-around max-md:overflow-x-auto max-md:pt-0 max-md:px-1 max-md:gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink key={item.to} to={item.to} className="relative w-full flex justify-center">
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

      <div className="pb-3 flex justify-center w-full">
        <NavLink to="/privacy" className="relative w-full flex justify-center">
          {({ isActive }) => (
            <Tooltip label="Privacy Policy" side="right">
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
