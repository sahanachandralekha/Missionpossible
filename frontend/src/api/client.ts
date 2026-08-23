/**
 * Centralized API Client for ScamCheck Backend.
 *
 * STATUS: FULLY IMPLEMENTED (Part 15)
 *
 * Encapsulates HTTP communication with FastAPI /api/v1 endpoints.
 * Never executes scam-detection logic locally; acts purely as a transport layer.
 */

import type {
  AnalysisApiResponse,
  AnalysisListResponse,
  AnalyzeTextPayload,
  ApiErrorResponse,
  ApiHealthResponse,
} from './types';


export class ApiClientError extends Error {
  errorCode: string;
  statusCode: number;
  requestId?: string | null;

  constructor(message: string, statusCode: number, errorCode: string = 'UNKNOWN_ERROR', requestId?: string | null) {
    super(message);
    this.name = 'ApiClientError';
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.requestId = requestId;
  }
}

const getBaseUrl = (): string => {
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
};

async function handleResponse<T>(res: Response): Promise<T> {
  const requestId = res.headers.get('X-Request-ID');

  if (!res.ok) {
    let errorCode = `HTTP_${res.status}`;
    let message = `Request failed with status ${res.status}`;

    try {
      const data: ApiErrorResponse | { detail?: any } = await res.json();
      if ('error_code' in data && data.message) {
        errorCode = data.error_code;
        message = data.message;
      } else if ('detail' in data) {
        if (typeof data.detail === 'string') {
          message = data.detail;
        } else if (typeof data.detail === 'object' && data.detail !== null) {
          errorCode = data.detail.error_code || errorCode;
          message = data.detail.message || JSON.stringify(data.detail);
        }
      }
    } catch {
      // Body not JSON
    }

    throw new ApiClientError(message, res.status, errorCode, requestId);
  }

  try {
    return (await res.json()) as T;
  } catch (err) {
    throw new ApiClientError('Failed to parse response JSON from server.', res.status, 'MALFORMED_JSON', requestId);
  }
}

export const apiClient = {
  /**
   * Submit raw text for opportunity scam analysis.
   */
  async analyzeText(payload: AnalyzeTextPayload): Promise<AnalysisApiResponse> {
    try {
      const res = await fetch(`${getBaseUrl()}/api/v1/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(payload.request_id ? { 'X-Request-ID': payload.request_id } : {}),
        },
        body: JSON.stringify(payload),
      });
      return await handleResponse<AnalysisApiResponse>(res);
    } catch (err) {
      if (err instanceof ApiClientError) throw err;
      throw new ApiClientError(
        'Unable to connect to ScamCheck server. Please check your network or server status.',
        0,
        'NETWORK_ERROR',
      );
    }
  },

  /**
   * Submit an image screenshot (PNG, JPEG, WebP) or offer letter PDF for analysis.
   */
  async analyzeFile(file: File): Promise<AnalysisApiResponse> {
    const formData = new FormData();
    formData.append('file', file, file.name);

    try {
      const res = await fetch(`${getBaseUrl()}/api/v1/analyze/file`, {
        method: 'POST',
        body: formData,
      });
      return await handleResponse<AnalysisApiResponse>(res);
    } catch (err) {
      if (err instanceof ApiClientError) throw err;
      throw new ApiClientError(
        'Unable to upload file to ScamCheck server. Please check your network or server status.',
        0,
        'NETWORK_ERROR',
      );
    }
  },

  /**
   * List recent analyses with pagination and optional filters.
   */
  async listAnalyses(
    limit: number = 20,
    offset: number = 0,
    sourceType?: string,
    riskLevel?: string,
  ): Promise<AnalysisListResponse> {
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    params.set('offset', String(offset));
    if (sourceType) params.set('source_type', sourceType);
    if (riskLevel) params.set('risk_level', riskLevel);

    try {
      const res = await fetch(`${getBaseUrl()}/api/v1/analyses?${params.toString()}`);
      return await handleResponse<AnalysisListResponse>(res);
    } catch (err) {
      if (err instanceof ApiClientError) throw err;
      throw new ApiClientError(
        'Failed to fetch analysis history.',
        0,
        'NETWORK_ERROR',
      );
    }
  },

  /**
   * Retrieve full detailed analysis record by analysis ID.
   */
  async getAnalysisById(analysisId: string): Promise<AnalysisApiResponse> {
    try {
      const res = await fetch(`${getBaseUrl()}/api/v1/analyses/${encodeURIComponent(analysisId)}`);
      return await handleResponse<AnalysisApiResponse>(res);
    } catch (err) {
      if (err instanceof ApiClientError) throw err;
      throw new ApiClientError(
        `Failed to retrieve analysis with ID '${analysisId}'.`,
        0,
        'NETWORK_ERROR',
      );
    }
  },

  /**
   * Health and readiness probe check.
   */
  async checkHealth(): Promise<ApiHealthResponse> {
    try {
      const res = await fetch(`${getBaseUrl()}/api/v1/health`);
      return await handleResponse<ApiHealthResponse>(res);
    } catch {
      return {
        status: 'unreachable',
        service: 'ScamCheck API',
        version: 'unknown',
        stage: 'disconnected',
      };
    }
  },
};
