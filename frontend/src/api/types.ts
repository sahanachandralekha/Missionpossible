/**
 * TypeScript Data Contracts for ScamCheck Frontend.
 *
 * STATUS: FULLY IMPLEMENTED (Part 15)
 *
 * Direct mappings of backend FastAPI Pydantic schemas.
 * NOTE: No scam scoring logic or rule algorithms belong here.
 */

export type SourceType = 'text' | 'image' | 'pdf';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type SignalSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface Evidence {
  type: string;
  value: string;
  source: string;
  location?: string | null;
  context?: string | null;
  metadata?: Record<string, any>;
}

export interface RiskSignal {
  signal_id: string;
  signal_type: string;
  title: string;
  description: string;
  severity: SignalSeverity;
  confidence: number;
  score_contribution?: number;
  evidence: Evidence[];
  metadata?: Record<string, any>;
}

export interface OrganizationEntity {
  name: string;
  confidence?: number;
  is_verified?: boolean;
}

export interface JobTitleEntity {
  title: string;
  confidence?: number;
}

export interface ContactEmailEntity {
  email: string;
  domain?: string;
  is_free_provider?: boolean;
}

export interface PhoneNumberEntity {
  raw_number: string;
  formatted_number?: string;
  country_code?: string;
}

export interface UrlEntity {
  url: string;
  domain?: string;
  scheme?: string;
}

export interface MonetaryAmountEntity {
  raw_amount: string;
  currency?: string;
  amount?: number;
}

export interface LocationEntity {
  raw_location: string;
  country?: string;
  city?: string;
}

export interface PaymentMethodEntity {
  raw_method: string;
  category?: string;
}

export interface CommunicationChannelEntity {
  raw_channel: string;
  category?: string;
}

export interface DateEntity {
  raw_date: string;
}

export interface ExtractedEntities {
  organizations?: OrganizationEntity[];
  job_titles?: JobTitleEntity[];
  contact_emails?: ContactEmailEntity[];
  phone_numbers?: PhoneNumberEntity[];
  urls?: UrlEntity[];
  monetary_amounts?: MonetaryAmountEntity[];
  locations?: LocationEntity[];
  payment_methods?: PaymentMethodEntity[];
  communication_channels?: CommunicationChannelEntity[];
  dates?: DateEntity[];
}

export interface AnalysisApiResponse {
  request_id: string;
  status: AnalysisStatus;
  source_type: SourceType;
  risk_score: number | null;
  risk_level: RiskLevel;
  summary: string | null;
  student_guidance: string | null;
  reasons: string[];
  signals: RiskSignal[];
  extracted_entities: ExtractedEntities;
  evidence: Evidence[];
  analysis_metadata: Record<string, any>;
  created_at?: string | null;
}

export interface AnalysisSummaryItem {
  analysis_id: string;
  request_id: string;
  created_at: string;
  status: AnalysisStatus;
  source_type: SourceType;
  risk_score: number | null;
  risk_level: RiskLevel;
  summary: string | null;
}

export interface AnalysisListResponse {
  total: number;
  items: AnalysisSummaryItem[];
  limit: number;
  offset: number;
}

export interface ApiHealthResponse {
  status: string;
  service: string;
  version: string;
  stage: string;
  timestamp?: string;
}

export interface ApiErrorResponse {
  status?: string;
  error_code: string;
  message: string;
  request_id?: string | null;
}

export interface AnalyzeTextPayload {
  text: string;
  metadata?: Record<string, any>;
  request_id?: string;
}
