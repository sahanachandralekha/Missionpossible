import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { apiClient } from '../api/client';
import type {
  AnalysisApiResponse,
  AnalysisListResponse,
  RiskLevel,
  AnalysisStatus,
  SourceType,
} from '../api/types';


describe('ScamCheck Frontend End-to-End Unit & Integration Test Suite', () => {
  beforeEach(() => {
    vi.resetAllMocks();

    // Default health mock
    vi.spyOn(apiClient, 'checkHealth').mockResolvedValue({
      status: 'healthy',
      service: 'ScamCheck API',
      version: '1.0.0',
      stage: 'production_ready',
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const mockCriticalResult: AnalysisApiResponse = {
    request_id: 'req_crit_123',
    status: 'completed' as AnalysisStatus,
    source_type: 'text' as SourceType,
    risk_score: 93,
    risk_level: 'critical' as RiskLevel,
    summary: 'High-risk scam opportunity detected with upfront fee and pressure.',
    student_guidance: 'Do not pay any money. Legitimate employers never charge application fees.',
    reasons: [
      'Upfront registration fee requested',
      'Urgency and high-pressure language',
      'Guaranteed selection without technical interview',
    ],
    signals: [
      {
        signal_id: 'SIG_UPFRONT_PAYMENT',
        signal_type: 'financial_risk',
        title: 'Upfront Payment Requested',
        description: 'Demands ₹2,999 registration fee.',
        severity: 'critical',
        confidence: 0.98,
        score_contribution: 40.0,
        evidence: [
          {
            type: 'payment_demand',
            value: '₹2,999 registration fee',
            source: 'text',
            location: 'offset:12-35',
            context: 'Pay ₹2,999 registration fee immediately.',
          },
        ],
      },
      {
        signal_id: 'SIG_FUTURE_EXPERIMENTAL_SIGNAL',
        signal_type: 'novel_detection',
        title: 'Novel Experimental Signal',
        description: 'Detected unusual behavior via future provider.',
        severity: 'high',
        confidence: 0.85,
        score_contribution: 15.0,
        evidence: [],
      },
    ],
    extracted_entities: {
      organizations: [{ name: 'Fake Acme Global Ltd' }],
      job_titles: [{ title: 'Python Intern' }],
      monetary_amounts: [{ raw_amount: '₹2,999' }],
      contact_emails: [{ email: 'hr@free-web-mail.com' }],
      phone_numbers: [{ raw_number: '+91 9876543210' }],
      urls: [{ url: 'https://bit.ly/pay-fake-intern' }],
      payment_methods: [{ raw_method: 'UPI / GPay' }],
    },
    evidence: [
      {
        type: 'payment_demand',
        value: '₹2,999 registration fee',
        source: 'text',
        location: 'offset:12-35',
        context: 'Pay ₹2,999 registration fee immediately.',
      },
    ],
    analysis_metadata: {
      provider: 'deterministic+semantic',
      timing_ms: 45,
    },
    created_at: '2026-08-23T10:00:00Z',
  };

  const mockLowRiskResult: AnalysisApiResponse = {
    request_id: 'req_low_456',
    status: 'completed' as AnalysisStatus,
    source_type: 'text' as SourceType,
    risk_score: 5,
    risk_level: 'low' as RiskLevel,
    summary: 'Standard legitimate job posting with no detectable scam signals.',
    student_guidance: 'Verify details through official corporate career channels.',
    reasons: [],
    signals: [],
    extracted_entities: {
      organizations: [{ name: 'Google' }],
      job_titles: [{ title: 'Software Engineer' }],
      urls: [{ url: 'https://careers.google.com' }],
    },
    evidence: [],
    analysis_metadata: { timing_ms: 12 },
    created_at: '2026-08-23T10:05:00Z',
  };

  // 1. Home page renders
  it('1. renders home page with title, hero section, and analyze form', () => {
    render(<App />);
    expect(screen.getByText('ScamCheck')).toBeInTheDocument();
    expect(screen.getByText('ScamCheck Opportunity Intelligence')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Paste a job offer, internship message/i)
    ).toBeInTheDocument();
  });

  // 2. Text input works
  it('2. allows typing opportunity text into textarea', async () => {
    const user = userEvent.setup();
    render(<App />);
    const textarea = screen.getByPlaceholderText(/Paste a job offer/i);
    await user.type(textarea, 'We are hiring Python interns.');
    expect(textarea).toHaveValue('We are hiring Python interns.');
  });

  // 3. Character counter works
  it('3. updates character count as user types', async () => {
    const user = userEvent.setup();
    render(<App />);
    const textarea = screen.getByPlaceholderText(/Paste a job offer/i);
    await user.type(textarea, 'Hello');
    expect(screen.getByText(/5 \/ 100,000 characters/i)).toBeInTheDocument();
  });

  // 4. Empty input validation
  it('4. shows client validation error when analyzing whitespace only text', async () => {
    const user = userEvent.setup();
    render(<App />);
    const textarea = screen.getByPlaceholderText(/Paste a job offer/i);
    await user.type(textarea, '   ');
    const submitBtn = screen.getByRole('button', { name: /Analyze Opportunity/i });
    expect(submitBtn).toBeDisabled();
  });

  // 5. Analyze request
  it('5. sends analyze request to API when analyze button is clicked', async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(apiClient, 'analyzeText').mockResolvedValue(mockCriticalResult);

    render(<App />);
    const textarea = screen.getByPlaceholderText(/Paste a job offer/i);
    await user.type(textarea, 'Selected for internship. Pay 2999 fee.');
    const submitBtn = screen.getByRole('button', { name: /Analyze Opportunity/i });
    await user.click(submitBtn);

    expect(spy).toHaveBeenCalledWith({ text: 'Selected for internship. Pay 2999 fee.' });
  });

  // 6. Loading state
  it('6. shows loading state during analysis request', async () => {
    const user = userEvent.setup();
    let resolvePromise: (value: AnalysisApiResponse) => void;
    const pendingPromise = new Promise<AnalysisApiResponse>((resolve) => {
      resolvePromise = resolve;
    });
    vi.spyOn(apiClient, 'analyzeText').mockReturnValue(pendingPromise);

    render(<App />);
    const textarea = screen.getByPlaceholderText(/Paste a job offer/i);
    await user.type(textarea, 'Hiring test opportunity.');
    const submitBtn = screen.getByRole('button', { name: /Analyze Opportunity/i });
    await user.click(submitBtn);

    expect(screen.getByText(/Analyzing Opportunity.../i)).toBeInTheDocument();

    // Resolve promise
    resolvePromise!(mockLowRiskResult);
    await waitFor(() => {
      expect(screen.queryByText(/Analyzing Opportunity.../i)).not.toBeInTheDocument();
    });
  });

  // 7. Successful result rendering
  it('7. renders complete result card with score, summary, and reasons', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'analyzeText').mockResolvedValue(mockCriticalResult);

    render(<App />);
    const textarea = screen.getByPlaceholderText(/Paste a job offer/i);
    await user.type(textarea, 'Pay fee');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByText('93')).toBeInTheDocument();
      expect(screen.getAllByText('CRITICAL RISK').length).toBeGreaterThan(0);
      expect(screen.getByText(/High-risk scam opportunity detected/i)).toBeInTheDocument();
      expect(screen.getByText('Upfront registration fee requested')).toBeInTheDocument();
    });

  });

  // 8. Critical risk rendering
  it('8. renders critical risk level badge and critical score gauge', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'analyzeText').mockResolvedValue(mockCriticalResult);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Critical test');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByRole('progressbar', { name: /Risk score: 93/i })).toBeInTheDocument();
      expect(screen.getAllByText('CRITICAL RISK').length).toBeGreaterThan(0);
    });
  });

  // 9. Low risk rendering
  it('9. renders low risk level badge and low score gauge', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'analyzeText').mockResolvedValue(mockLowRiskResult);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Google career post');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByRole('progressbar', { name: /Risk score: 5/i })).toBeInTheDocument();
      expect(screen.getByText('LOW RISK')).toBeInTheDocument();
    });
  });

  // 10. Backend validation error
  it('10. renders structured error alert when backend returns validation error', async () => {
    const user = userEvent.setup();
    const error = new Error('Input text contains invalid characters.');
    (error as any).errorCode = 'INVALID_INPUT';
    (error as any).requestId = 'req_err_999';
    vi.spyOn(apiClient, 'analyzeText').mockRejectedValue(error);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Bad input');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Input text contains invalid characters.')).toBeInTheDocument();
    });
  });

  // 11. Backend 500 error
  it('11. renders friendly error alert on backend 500 without crashing', async () => {
    const user = userEvent.setup();
    const error = new Error('An unexpected error occurred during analysis.');
    (error as any).errorCode = 'INTERNAL_ERROR';
    vi.spyOn(apiClient, 'analyzeText').mockRejectedValue(error);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Internal error test');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByText(/An unexpected error occurred during analysis/i)).toBeInTheDocument();
    });
  });

  // 12. Network failure
  it('12. handles offline network failure with retry button', async () => {
    const user = userEvent.setup();
    const error = new Error('Unable to connect to ScamCheck server.');
    vi.spyOn(apiClient, 'analyzeText').mockRejectedValue(error);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Offline test');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByText(/Unable to connect to ScamCheck server/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });
  });

  // 13. Image upload
  it('13. switches to upload tab and analyzes image file', async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(apiClient, 'analyzeFile').mockResolvedValue({
      ...mockCriticalResult,
      source_type: 'image',
    });

    render(<App />);
    await user.click(screen.getByRole('tab', { name: /Upload Image \/ PDF/i }));

    const file = new File(['fake image bytes'], 'screenshot.png', { type: 'image/png' });
    const input = document.getElementById('file-upload-input') as HTMLInputElement;
    await user.upload(input, file);

    expect(screen.getByText('screenshot.png')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Analyze (Uploaded File|Opportunity)/i }));

    expect(spy).toHaveBeenCalled();
  });

  // 14. PDF upload
  it('14. uploads and analyzes PDF document', async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(apiClient, 'analyzeFile').mockResolvedValue({
      ...mockLowRiskResult,
      source_type: 'pdf',
    });

    render(<App />);
    await user.click(screen.getByRole('tab', { name: /Upload Image \/ PDF/i }));

    const file = new File(['fake pdf bytes'], 'offer_letter.pdf', { type: 'application/pdf' });
    const input = document.getElementById('file-upload-input') as HTMLInputElement;
    await user.upload(input, file);

    expect(screen.getByText('offer_letter.pdf')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Analyze (Uploaded File|Opportunity)/i }));

    expect(spy).toHaveBeenCalled();
  });

  // 15. Unsupported file rejection
  it('15. rejects executable or unsupported file extension on client side', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('tab', { name: /Upload Image \/ PDF/i }));

    const file = new File(['fake exe'], 'malware.exe', { type: 'application/x-msdownload' });
    const input = document.getElementById('file-upload-input') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    expect(
      screen.getByText(/Unsupported file format/i)
    ).toBeInTheDocument();
  });


  // 16. History loading
  it('16. loads and displays history records from API', async () => {
    const user = userEvent.setup();
    const mockHistory: AnalysisListResponse = {
      total: 1,
      items: [
        {
          analysis_id: 'rec_hist_01',
          request_id: 'rec_hist_01',
          created_at: '2026-08-23T10:00:00Z',
          status: 'completed',
          source_type: 'text',
          risk_score: 85,
          risk_level: 'high',
          summary: 'Scam job offer with fake fee',
        },
      ],
      limit: 10,
      offset: 0,
    };

    vi.spyOn(apiClient, 'listAnalyses').mockResolvedValue(mockHistory);

    render(<App />);
    await user.click(screen.getByRole('button', { name: /History/i }));

    await waitFor(() => {
      expect(screen.getByText('Analysis History')).toBeInTheDocument();
      expect(screen.getByText('Scam job offer with fake fee')).toBeInTheDocument();
      expect(screen.getByText('Score: 85/100')).toBeInTheDocument();
    });
  });

  // 17. Empty history
  it('17. renders empty history state when no records exist', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'listAnalyses').mockResolvedValue({
      total: 0,
      items: [],
      limit: 10,
      offset: 0,
    });

    render(<App />);
    await user.click(screen.getByRole('button', { name: /History/i }));

    await waitFor(() => {
      expect(screen.getByText('No Analysis History Found')).toBeInTheDocument();
    });
  });

  // 18. History pagination
  it('18. displays pagination controls when total exceeds limit', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'listAnalyses').mockResolvedValue({
      total: 25,
      items: [
        {
          analysis_id: 'rec_hist_page1',
          request_id: 'rec_hist_page1',
          created_at: '2026-08-23T10:00:00Z',
          status: 'completed',
          source_type: 'text',
          risk_score: 50,
          risk_level: 'medium',
          summary: 'Sample page 1 record',
        },
      ],
      limit: 10,
      offset: 0,
    });

    render(<App />);
    await user.click(screen.getByRole('button', { name: /History/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Next/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Previous/i })).toBeInTheDocument();
      expect(screen.getByText(/total analyses/i)).toBeInTheDocument();
    });

  });

  // 19. History detail loading
  it('19. clicking history item loads full detail result', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'listAnalyses').mockResolvedValue({
      total: 1,
      items: [
        {
          analysis_id: 'rec_detail_01',
          request_id: 'rec_detail_01',
          created_at: '2026-08-23T10:00:00Z',
          status: 'completed',
          source_type: 'text',
          risk_score: 93,
          risk_level: 'critical',
          summary: 'Critical item summary',
        },
      ],
      limit: 10,
      offset: 0,
    });

    const getSpy = vi.spyOn(apiClient, 'getAnalysisById').mockResolvedValue(mockCriticalResult);

    render(<App />);
    await user.click(screen.getByRole('button', { name: /History/i }));

    await waitFor(() => {
      expect(screen.getByText('Critical item summary')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Critical item summary'));

    expect(getSpy).toHaveBeenCalledWith('rec_detail_01');
    await waitFor(() => {
      expect(screen.getByText('What You Should Do (Student Guidance)')).toBeInTheDocument();
    });
  });

  // 20. Missing analysis error
  it('20. handles missing analysis ID error gracefully', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'listAnalyses').mockResolvedValue({
      total: 1,
      items: [
        {
          analysis_id: 'rec_missing_999',
          request_id: 'rec_missing_999',
          created_at: '2026-08-23T10:00:00Z',
          status: 'completed',
          source_type: 'text',
          risk_score: 50,
          risk_level: 'medium',
          summary: 'Missing item',
        },
      ],
      limit: 10,
      offset: 0,
    });

    vi.spyOn(apiClient, 'getAnalysisById').mockRejectedValue(
      new Error("Analysis with ID 'rec_missing_999' was not found.")
    );

    render(<App />);
    await user.click(screen.getByRole('button', { name: /History/i }));
    await waitFor(() => screen.getByText('Missing item'));
    await user.click(screen.getByText('Missing item'));

    await waitFor(() => {
      expect(screen.getByText(/was not found/i)).toBeInTheDocument();
    });
  });

  // 21. Evidence expansion
  it('21. expands supporting evidence accordion when clicked', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'analyzeText').mockResolvedValue(mockCriticalResult);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Pay fee');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByText(/Supporting Evidence/i)).toBeInTheDocument();
    });

    const toggle = screen.getByRole('button', { name: /Supporting Evidence/i });
    await user.click(toggle);

    expect(screen.getByText(/\[payment_demand\]/i)).toBeInTheDocument();
  });

  // 22. Extracted entities rendering
  it('22. expands and displays extracted organizations, roles, and contacts', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'analyzeText').mockResolvedValue(mockCriticalResult);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Entity test');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByText(/Extracted Entities/i)).toBeInTheDocument();
    });

    const toggle = screen.getByRole('button', { name: /Extracted Entities/i });
    await user.click(toggle);

    expect(screen.getByText('Fake Acme Global Ltd')).toBeInTheDocument();
    expect(screen.getByText('Python Intern')).toBeInTheDocument();
    expect(screen.getByText('hr@free-web-mail.com')).toBeInTheDocument();
  });

  // 23. Request ID display
  it('23. displays traceable correlation request ID in metadata bar', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'analyzeText').mockResolvedValue(mockCriticalResult);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Request ID test');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByText(/ID: req_crit_123/i)).toBeInTheDocument();
    });
  });

  // 24. Health status
  it('24. displays live backend health connected badge', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText('Backend Connected')).toBeInTheDocument();
    });
  });

  // 25. Accessibility basics
  it('25. provides accessible role attributes, buttons, and progress indicators', () => {
    render(<App />);
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('tablist')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Paste Text/i })).toHaveAttribute('aria-selected', 'true');
  });

  // 26. Unknown future signal type does not break UI
  it('26. handles unknown future signal type gracefully without crashing', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'analyzeText').mockResolvedValue(mockCriticalResult);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Future signal test');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByText('Novel Experimental Signal')).toBeInTheDocument();
      expect(screen.getByText(/Detected unusual behavior via future provider/i)).toBeInTheDocument();
    });
  });

  // 27. Malformed optional fields do not crash UI
  it('27. handles missing/null optional fields without crashing', async () => {
    const user = userEvent.setup();
    const minimalResult: AnalysisApiResponse = {
      request_id: 'req_min_001',
      status: 'completed',
      source_type: 'text',
      risk_score: null,
      risk_level: 'low',
      summary: null,
      student_guidance: null,
      reasons: [],
      signals: [],
      extracted_entities: {},
      evidence: [],
      analysis_metadata: {},
      created_at: null,
    };

    vi.spyOn(apiClient, 'analyzeText').mockResolvedValue(minimalResult);

    render(<App />);
    await user.type(screen.getByPlaceholderText(/Paste a job offer/i), 'Minimal result test');
    await user.click(screen.getByRole('button', { name: /Analyze Opportunity/i }));

    await waitFor(() => {
      expect(screen.getByText('LOW RISK')).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument();
    });
  });
});
