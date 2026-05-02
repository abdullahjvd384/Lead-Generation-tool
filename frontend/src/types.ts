export interface Lead {
  id: number;
  company_name: string;
  website: string;
  domain: string;
  industry: string;
  employee_count: number;
  location: string;
  score: number | null;
  tier: "A" | "B" | "C" | null;
  why: string | null;
  status: string | null;
  title: string | null;
  description: string | null;
  tech_stack: string[];
  contacts: {
    emails?: string[];
    phones?: string[];
    social?: Record<string, string>;
  };
  signals: {
    hiring?: boolean;
    founded_year?: number | null;
    page_words?: number;
  };
  reasons: Array<{
    signal: string;
    weight: number;
    raw: number;
    contribution: number;
    details: string[];
  }>;
  quality: {
    recommended_action: "Prioritize" | "Research" | "Nurture" | "Disqualify" | "Score first";
    confidence: number;
    risk_flags: string[];
    missing_data: string[];
    contact_channels: string[];
    summary: string;
  };
  stage: "new" | "contacted" | "qualified" | "dead";
  stage_reason: string;
  stage_updated_by: string | null;
  stage_updated_at: string | null;
  latest_score_change: {
    previous_score: number | null;
    previous_tier: string;
    new_score: number;
    new_tier: string;
    version: number;
    changed_at: string;
  } | null;
}

export interface RankedLead extends Lead {
  rank: number;
  next_step: string;
  rank_reason: string;
}

export interface RankedLeadList {
  limit: number;
  total: number;
  items: RankedLead[];
}

export interface PipelineStageUpdate {
  stage: "new" | "contacted" | "qualified" | "dead";
  reason?: string;
  updated_by?: string;
}

export interface PipelineStage {
  lead_id: number;
  stage: "new" | "contacted" | "qualified" | "dead";
  reason: string;
  updated_by: string;
  updated_at: string;
}

export interface PipelineStageHistoryItem {
  id: number;
  lead_id: number;
  from_stage: string;
  to_stage: string;
  reason: string;
  updated_by: string;
  updated_at: string;
}

export interface ScoreHistoryItem {
  id: number;
  lead_id: number;
  previous_score: number | null;
  previous_tier: string;
  new_score: number;
  new_tier: string;
  previous_why: string;
  new_why: string;
  version: number;
  changed_at: string;
}

export interface PipelineSummaryItem {
  stage: string;
  count: number;
}

export interface PipelineSummary {
  total: number;
  items: PipelineSummaryItem[];
}

export interface LookalikeReason {
  signal: string;
  weight: number;
  raw: number;
  contribution: number;
  details: string[];
}

export interface LookalikeMatch {
  lead: Lead;
  similarity: number;
  reasons: LookalikeReason[];
}

export interface LookalikeList {
  seed_lead: Lead;
  total: number;
  limit: number;
  items: LookalikeMatch[];
}

export interface ICP {
  id: number;
  industry_keywords: string;
  size_min: number;
  size_max: number;
  value_prop: string;
  updated_at: string;
}

export interface ScoringConfig {
  id: number;
  template: string;
  weights: Record<string, number>;
  version: number;
  updated_at: string;
}

export interface Email {
  id?: number | null;
  tone: "direct" | "warm" | "executive";
  subject: string;
  body: string;
  created_at?: string | null;
}

export interface UploadResult {
  inserted: number;
  duplicates: number;
  invalid: number;
  total_leads: number;
  mapping_used: Record<string, string>;
  mapping_source: "exact" | "alias" | "openai" | "manual" | "none";
}

export interface CsvPreview {
  total_rows: number;
  inserted: number;
  duplicates: number;
  invalid: number;
  mapping_used: Record<string, string>;
  mapping_source: "exact" | "alias" | "openai" | "manual" | "none";
  columns: string[];
  canonical_columns: string[];
  preview_rows: Record<string, string | number>[];
  invalid_rows: number[];
}

export interface ScoreResult {
  scored: number;
  cached: number;
  failed: number;
}
