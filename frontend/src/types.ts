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
  mapping_source: "exact" | "alias" | "gemini" | "none";
}

export interface ScoreResult {
  scored: number;
  cached: number;
  failed: number;
}
