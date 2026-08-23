import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Layers } from 'lucide-react';
import type { RiskSignal } from '../api/types';
import { RiskBadge } from './RiskBadge';


interface SignalListProps {
  signals?: RiskSignal[];
}

export const SignalList: React.FC<SignalListProps> = ({ signals }) => {
  const [expandedSignals, setExpandedSignals] = useState<Record<string, boolean>>({});

  if (!signals || signals.length === 0) return null;

  const toggleExpand = (id: string) => {
    setExpandedSignals((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="section-box">
      <div className="section-title">
        <Layers size={16} aria-hidden="true" />
        <span>Detected Risk Signals ({signals.length})</span>
      </div>

      <div className="signals-grid">
        {signals.map((sig, idx) => {
          const signalKey = sig.signal_id || `signal-${idx}`;
          const isExpanded = !!expandedSignals[signalKey];
          const hasEvidence = sig.evidence && sig.evidence.length > 0;

          return (
            <div key={signalKey} className="signal-card">
              <div className="signal-card-header">
                <div className="signal-title">{sig.title || sig.signal_id}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {typeof sig.confidence === 'number' && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {Math.round(sig.confidence * 100)}% conf
                    </span>
                  )}
                  <RiskBadge level={sig.severity} />
                </div>
              </div>

              <div className="signal-desc">{sig.description}</div>

              {hasEvidence && (
                <div style={{ marginTop: '0.5rem' }}>
                  <button
                    type="button"
                    className="accordion-toggle"
                    style={{ fontSize: '0.8rem', padding: '0.2rem 0' }}
                    onClick={() => toggleExpand(signalKey)}
                    aria-expanded={isExpanded}
                  >
                    <span>
                      {isExpanded ? 'Hide Signal Evidence' : `Show Evidence (${sig.evidence.length})`}
                    </span>
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {isExpanded && (
                    <div className="evidence-drawer" style={{ marginTop: '0.4rem' }}>
                      {sig.evidence.map((ev, evIdx) => (
                        <div key={`sig-ev-${evIdx}`} className="evidence-item">
                          <div>
                            <strong>[{ev.type}]</strong> {ev.location && <span>({ev.location})</span>}
                          </div>
                          <div style={{ marginTop: '0.2rem', color: '#f8fafc' }}>
                            "{ev.value}"
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
