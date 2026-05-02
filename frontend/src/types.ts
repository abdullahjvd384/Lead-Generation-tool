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

export interface Email {
  subject: string;
  body: string;
}

export interface UploadResult {
  inserted: number;
  duplicates: number;
  invalid: number;
  total_leads: number;
  mapping_used: Record<string, string>;
  mapping_source: "exact" | "alias" | "openai" | "none";
}

export interface ScoreResult {
  scored: number;
  cached: number;
  failed: number;
}
