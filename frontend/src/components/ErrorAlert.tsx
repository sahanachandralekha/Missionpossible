import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { ApiClientError } from '../api/client';

interface ErrorAlertProps {
  error: Error | ApiClientError | string | null;
  onRetry?: () => void;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({ error, onRetry }) => {
  if (!error) return null;

  const errorMessage = typeof error === 'string' ? error : error.message;
  const errorCode = error instanceof ApiClientError ? error.errorCode : null;
  const requestId = error instanceof ApiClientError ? error.requestId : null;

  return (
    <div className="error-alert" role="alert" aria-live="assertive">
      <AlertCircle size={20} className="text-red-400" aria-hidden="true" />
      <div style={{ flex: 1 }}>
        <div className="error-title">Analysis Request Failed</div>
        <p>{errorMessage}</p>
        {(errorCode || requestId) && (
          <div className="error-meta">
            {errorCode && <span>Error Code: <strong>{errorCode}</strong></span>}
            {errorCode && requestId && <span> • </span>}
            {requestId && <span>Reference ID: <strong>{requestId}</strong></span>}
          </div>
        )}
      </div>
      {onRetry && (
        <button
          type="button"
          className="btn btn-secondary"
          style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
          onClick={onRetry}
          aria-label="Retry action"
        >
          <RefreshCw size={14} aria-hidden="true" />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
};
