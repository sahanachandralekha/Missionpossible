import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { AnalyzeForm } from './components/AnalyzeForm';
import { ResultCard } from './components/ResultCard';
import { HistoryView } from './components/HistoryView';
import { ErrorAlert } from './components/ErrorAlert';
import { apiClient } from './api/client';
import type { AnalysisApiResponse, ApiHealthResponse } from './api/types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<'analyze' | 'history'>('analyze');
  const [currentResult, setCurrentResult] = useState<AnalysisApiResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<any>(null);
  const [health, setHealth] = useState<ApiHealthResponse | null>(null);

  // Initial health check probe
  useEffect(() => {
    let isMounted = true;

    const checkBackendHealth = async () => {
      const status = await apiClient.checkHealth();
      if (isMounted) {
        setHealth(status);
      }
    };

    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 60_000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleAnalyzeText = async (text: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await apiClient.analyzeText({ text });
      setCurrentResult(result);
    } catch (err: any) {
      setError(err);
      setCurrentResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyzeFile = async (file: File) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await apiClient.analyzeFile(file);
      setCurrentResult(result);
    } catch (err: any) {
      setError(err);
      setCurrentResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectHistoryItem = async (analysisId: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await apiClient.getAnalysisById(analysisId);
      setCurrentResult(result);
      setCurrentTab('analyze');
    } catch (err: any) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentResult(null);
    setError(null);
  };

  return (
    <div className="app-container">
      <Header
        currentTab={currentTab}
        onTabChange={(tab) => {
          setCurrentTab(tab);
          setError(null);
        }}
        health={health}
      />

      <main className="main-content">
        {currentTab === 'analyze' && (
          <>
            {!currentResult && (
              <section className="hero-section" aria-label="Introduction">
                <h1 className="hero-title">
                  ScamCheck Opportunity Intelligence
                </h1>
                <p className="hero-subtitle">
                  Verify internships, jobs, gigs, training offers, and recruitment messages before paying fees or sharing sensitive personal information.
                </p>
              </section>


            )}

            <ErrorAlert error={error} onRetry={() => setError(null)} />

            {currentResult ? (
              <ResultCard result={currentResult} onReset={handleReset} />
            ) : (
              <AnalyzeForm
                isLoading={isLoading}
                onAnalyzeText={handleAnalyzeText}
                onAnalyzeFile={handleAnalyzeFile}
              />
            )}
          </>
        )}

        {currentTab === 'history' && (
          <>
            <ErrorAlert error={error} onRetry={() => setError(null)} />
            <HistoryView onSelectAnalysis={handleSelectHistoryItem} />
          </>
        )}
      </main>

      <footer className="footer-banner" role="contentinfo">
        <div className="footer-inner">
          <p>
            ScamCheck is an educational opportunity risk assessment platform designed to protect students and jobseekers.
          </p>
          <p style={{ marginTop: '4px', opacity: 0.85 }}>
            Data is evaluated in-memory using deterministic and semantic intelligence. Analysis history is stored locally.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
