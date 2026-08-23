import React from 'react';
import { ShieldCheck, Clock, Search } from 'lucide-react';
import type { ApiHealthResponse } from '../api/types';

interface HeaderProps {
  currentTab: 'analyze' | 'history';
  onTabChange: (tab: 'analyze' | 'history') => void;
  health: ApiHealthResponse | null;
}

export const Header: React.FC<HeaderProps> = ({ currentTab, onTabChange, health }) => {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="header" role="banner">
      <div className="header-inner">
        <a
          href="#"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            onTabChange('analyze');
          }}
          aria-label="ScamCheckShield Home"
        >
          <ShieldCheck size={22} color="#0f172a" strokeWidth={2.2} />
          <span className="brand-text">
            <span>ScamCheck</span><span>Shield</span>
          </span>
        </a>

        <nav className="header-nav" aria-label="Main Navigation">
          <button
            type="button"
            className={`nav-tab ${currentTab === 'analyze' ? 'active' : ''}`}
            onClick={() => onTabChange('analyze')}
            aria-pressed={currentTab === 'analyze'}
          >
            <Search size={14} aria-hidden="true" />
            <span>Analyze</span>
          </button>

          <button
            type="button"
            className={`nav-tab ${currentTab === 'history' ? 'active' : ''}`}
            onClick={() => onTabChange('history')}
            aria-pressed={currentTab === 'history'}
          >
            <Clock size={14} aria-hidden="true" />
            <span>History</span>
          </button>
        </nav>

        <div
          className="health-pill"
          title={isHealthy ? 'Backend API connected' : 'Backend API unavailable'}
          role="status"
          aria-live="polite"
        >
          <span className={`health-pulse ${isHealthy ? '' : 'offline'}`} />
          <span>{isHealthy ? 'Backend Connected' : 'Backend Offline'}</span>
        </div>
      </div>
    </header>
  );
};
