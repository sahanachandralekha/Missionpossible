import React from 'react';
import {
  AlertCircle,
  HelpCircle,
  Clock,
  Fingerprint,
  FileCode,
} from 'lucide-react';
import type { AnalysisApiResponse } from '../api/types';


import { RiskBadge } from './RiskBadge';
import { SignalList } from './SignalList';
import { EntityViewer } from './EntityViewer';
import { EvidenceViewer } from './EvidenceViewer';

interface ResultCardProps {
  result: AnalysisApiResponse;
  onReset?: () => void;
}

export const ResultCard: React.FC<ResultCardProps> = ({ result, onReset }) => {
  const riskClass = `risk-${(result.risk_level || 'low').toLowerCase()}`;
  const score = result.risk_score ?? 0;

  return (
    <article className={`result-card ${riskClass}`} aria-labelledby="analysis-result-title">
      <div className="result-header">
        <div className="score-display-box">
          <div
            className={`score-gauge ${riskClass}`}
            role="progressbar"
            aria-valuenow={score}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Risk score: ${score} out of 100`}
          >
            {score}
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Calibrated Scam Risk
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.2rem' }}>
              <RiskBadge level={result.risk_level} />
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                ({score} / 100)
              </span>
            </div>
          </div>
        </div>

        {onReset && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onReset}
            style={{ padding: '0.45rem 0.9rem', fontSize: '0.85rem' }}
          >
            Analyze Another Opportunity
          </button>
        )}
      </div>

      {result.summary && (
        <div id="analysis-result-title" className="result-summary-text">
          {result.summary}
        </div>
      )}

      {/* Student Guidance */}
      {result.student_guidance && (
        <div className="section-box" style={{ padding: 0, overflow: 'hidden', border: 'none' }}>
          <div className="guidance-box">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 700, marginBottom: '0.35rem' }}>
              <HelpCircle size={16} />
              <span>What You Should Do (Student Guidance)</span>
            </div>
            <p>{result.student_guidance}</p>
          </div>
        </div>
      )}

      {/* Why this was flagged (Reasons List) */}
      {result.reasons && result.reasons.length > 0 && (
        <div className="section-box">
          <div className="section-title">
            <AlertCircle size={16} aria-hidden="true" />
            <span>Why This Opportunity Was Flagged</span>
          </div>
          <ul className="reasons-list">
            {result.reasons.map((reason, idx) => (
              <li key={`reason-${idx}`}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Detected Signals */}
      <SignalList signals={result.signals} />

      {/* Extracted Entities */}
      <EntityViewer entities={result.extracted_entities} />

      {/* Supporting Evidence */}
      <EvidenceViewer evidence={result.evidence} />

      {/* Metadata Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          marginTop: '1.5rem',
          paddingTop: '1rem',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            <FileCode size={14} />
            <span>Source: <strong style={{ color: 'var(--text-secondary)' }}>{result.source_type?.toUpperCase()}</strong></span>
          </span>

          {result.created_at && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
              <Clock size={14} />
              <span>{new Date(result.created_at).toLocaleString()}</span>
            </span>
          )}
        </div>

        {result.request_id && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontFamily: 'monospace' }}>
            <Fingerprint size={14} />
            <span>ID: {result.request_id}</span>
          </span>
        )}
      </div>
    </article>
  );
};
