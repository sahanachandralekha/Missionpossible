import React, { useEffect, useState } from 'react';
import {
  Clock,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Search,
  FileText,
  Image,
  File,
  AlertCircle,
} from 'lucide-react';
import { apiClient } from '../api/client';
import type { AnalysisSummaryItem } from '../api/types';
import { RiskBadge } from './RiskBadge';


interface HistoryViewProps {
  onSelectAnalysis: (analysisId: string) => void;
}

const PAGE_SIZE = 10;

export const HistoryView: React.FC<HistoryViewProps> = ({ onSelectAnalysis }) => {
  const [items, setItems] = useState<AnalysisSummaryItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [offset, setOffset] = useState<number>(0);
  const [riskFilter, setRiskFilter] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const res = await apiClient.listAnalyses(
        PAGE_SIZE,
        offset,
        sourceFilter || undefined,
        riskFilter || undefined,
      );
      setItems(res.items || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch analysis history.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [offset, riskFilter, sourceFilter]);

  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const handlePrevPage = () => {
    if (offset >= PAGE_SIZE) {
      setOffset(offset - PAGE_SIZE);
    }
  };

  const handleNextPage = () => {
    if (offset + PAGE_SIZE < total) {
      setOffset(offset + PAGE_SIZE);
    }
  };

  const getSourceIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'pdf':
        return <File size={14} color="#f87171" />;
      case 'image':
        return <Image size={14} color="#38bdf8" />;
      case 'text':
      default:
        return <FileText size={14} color="#94a3b8" />;
    }
  };

  return (
    <div className="history-view-container" aria-labelledby="history-heading">
      <div className="history-header">
        <div>
          <h2 id="history-heading" style={{ fontSize: '1.4rem', fontWeight: 800 }}>
            Analysis History
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
            Inspect previously analyzed opportunities stored securely in local history.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={fetchHistory}
          disabled={isLoading}
          style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
          aria-label="Refresh analysis history"
        >
          <RefreshCw size={14} className={isLoading ? 'spinner' : ''} aria-hidden="true" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Controls */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
        <div className="filter-pills" role="group" aria-label="Filter by Risk Level">
          <button
            type="button"
            className={`filter-pill ${riskFilter === '' ? 'active' : ''}`}
            onClick={() => {
              setRiskFilter('');
              setOffset(0);
            }}
          >
            All Severities
          </button>
          <button
            type="button"
            className={`filter-pill ${riskFilter === 'critical' ? 'active' : ''}`}
            onClick={() => {
              setRiskFilter('critical');
              setOffset(0);
            }}
          >
            Critical
          </button>
          <button
            type="button"
            className={`filter-pill ${riskFilter === 'high' ? 'active' : ''}`}
            onClick={() => {
              setRiskFilter('high');
              setOffset(0);
            }}
          >
            High
          </button>
          <button
            type="button"
            className={`filter-pill ${riskFilter === 'medium' ? 'active' : ''}`}
            onClick={() => {
              setRiskFilter('medium');
              setOffset(0);
            }}
          >
            Medium
          </button>
          <button
            type="button"
            className={`filter-pill ${riskFilter === 'low' ? 'active' : ''}`}
            onClick={() => {
              setRiskFilter('low');
              setOffset(0);
            }}
          >
            Low
          </button>
        </div>

        <div className="filter-pills" role="group" aria-label="Filter by Source Type">
          <button
            type="button"
            className={`filter-pill ${sourceFilter === '' ? 'active' : ''}`}
            onClick={() => {
              setSourceFilter('');
              setOffset(0);
            }}
          >
            All Sources
          </button>
          <button
            type="button"
            className={`filter-pill ${sourceFilter === 'text' ? 'active' : ''}`}
            onClick={() => {
              setSourceFilter('text');
              setOffset(0);
            }}
          >
            Text
          </button>
          <button
            type="button"
            className={`filter-pill ${sourceFilter === 'image' ? 'active' : ''}`}
            onClick={() => {
              setSourceFilter('image');
              setOffset(0);
            }}
          >
            Image
          </button>
          <button
            type="button"
            className={`filter-pill ${sourceFilter === 'pdf' ? 'active' : ''}`}
            onClick={() => {
              setSourceFilter('pdf');
              setOffset(0);
            }}
          >
            PDF
          </button>
        </div>
      </div>

      {/* Loading & Error States */}
      {isLoading && (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="spinner" style={{ margin: '0 auto 0.5rem auto' }} />
          <div>Loading analysis history...</div>
        </div>
      )}

      {!isLoading && error && (
        <div
          role="alert"
          style={{
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#fca5a5',
            padding: '1.25rem',
            borderRadius: 'var(--radius-md)',
            textAlign: 'center',
          }}
        >
          <AlertCircle size={24} style={{ margin: '0 auto 0.5rem auto' }} />
          <p>{error}</p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchHistory}
            style={{ marginTop: '0.75rem', fontSize: '0.85rem' }}
          >
            Retry Fetching
          </button>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && items.length === 0 && (
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px dashed var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: '3.5rem 1.5rem',
            textAlign: 'center',
            color: 'var(--text-muted)',
          }}
        >
          <Clock size={36} style={{ margin: '0 auto 0.75rem auto', color: 'var(--text-muted)' }} />
          <h3 style={{ fontSize: '1.1rem', color: 'var(--text-main)', marginBottom: '0.25rem' }}>
            No Analysis History Found
          </h3>
          <p style={{ fontSize: '0.9rem' }}>
            {riskFilter || sourceFilter
              ? 'No records match the selected filters.'
              : 'Submit an opportunity on the Analyze tab to build your verification history.'}
          </p>
        </div>
      )}

      {/* Records List */}
      {!isLoading && !error && items.length > 0 && (
        <div className="history-list" role="list">
          {items.map((item) => (
            <div
              key={item.analysis_id}
              className="history-item-card"
              role="listitem"
              tabIndex={0}
              onClick={() => onSelectAnalysis(item.analysis_id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  onSelectAnalysis(item.analysis_id);
                }
              }}
              aria-label={`Analysis ${item.analysis_id}: ${item.risk_level} risk score ${item.risk_score ?? 0}`}
            >
              <div style={{ flex: 1 }}>
                <div className="history-meta">
                  <RiskBadge level={item.risk_level} />
                  <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>
                    Score: {item.risk_score ?? 'N/A'}/100
                  </span>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.3rem',
                      background: 'var(--bg-card)',
                      padding: '0.15rem 0.5rem',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.75rem',
                      color: 'var(--text-secondary)',
                      textTransform: 'uppercase',
                    }}
                  >
                    {getSourceIcon(item.source_type)}
                    <span>{item.source_type}</span>
                  </span>
                  <span className="history-date">
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                </div>

                <div className="history-summary">
                  {item.summary || 'No narrative summary recorded.'}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)' }}>
                <Search size={16} />
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Inspect</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Bar */}
      {!isLoading && !error && total > PAGE_SIZE && (
        <div className="pagination-controls">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handlePrevPage}
            disabled={offset === 0}
            style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
          >
            <ChevronLeft size={16} />
            <span>Previous</span>
          </button>

          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> ({total} total analyses)
          </span>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleNextPage}
            disabled={offset + PAGE_SIZE >= total}
            style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
          >
            <span>Next</span>
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
};
