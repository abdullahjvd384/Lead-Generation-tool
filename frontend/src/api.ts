import type {
  Email,
  CsvPreview,
  ICP,
  Lead,
  LookalikeList,
  PipelineStage,
  PipelineStageHistoryItem,
  PipelineStageUpdate,
  PipelineSummary,
  RankedLeadList,
  ScoreHistoryItem,
  ScoreResult,
  ScoringConfig,
  UploadResult,
} from "./types";

const BASE = "/api";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, init);
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${text}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  health: () => jsonFetch<{ status: string }>("/health"),
  systemStatus: () =>
    jsonFetch<{
      ai_enabled: boolean;
      has_key: boolean;
      circuit_open: boolean;
      model: string | null;
    }>("/system/status"),

  listLeads: () => jsonFetch<Lead[]>("/leads"),
  getLead: (id: number) => jsonFetch<Lead>(`/leads/${id}`),
  rankedLeads: (opts?: { limit?: number; stage?: string; tier?: string }) => {
    const params = new URLSearchParams();
    if (opts?.limit) params.set("limit", String(opts.limit));
    if (opts?.stage) params.set("stage", opts.stage);
    if (opts?.tier) params.set("tier", opts.tier);
    const query = params.toString();
    return jsonFetch<RankedLeadList>(`/leads/ranked${query ? `?${query}` : ""}`);
  },
  pipelineSummary: () => jsonFetch<PipelineSummary>("/leads/pipeline"),
  updateLeadStage: (leadId: number, payload: PipelineStageUpdate) =>
    jsonFetch<PipelineStage>(`/leads/${leadId}/stage`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  leadStageHistory: (leadId: number) =>
    jsonFetch<PipelineStageHistoryItem[]>(`/leads/${leadId}/stage/history`),
  leadScoreHistory: (leadId: number) =>
    jsonFetch<ScoreHistoryItem[]>(`/leads/${leadId}/score/history`),
  lookalikes: (leadId: number, limit = 10) =>
    jsonFetch<LookalikeList>(`/leads/${leadId}/lookalikes?limit=${limit}`),
  resetLeads: () =>
    jsonFetch<UploadResult>("/leads", { method: "DELETE" }),
  seedDemo: () =>
    jsonFetch<UploadResult>("/leads/seed", { method: "POST" }),
  uploadCsv: async (file: File): Promise<UploadResult> => {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(BASE + "/leads/upload", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  previewCsv: async (file: File, mapping?: Record<string, string>): Promise<CsvPreview> => {
    const fd = new FormData();
    fd.append("file", file);
    if (mapping) fd.append("mapping_json", JSON.stringify(mapping));
    const r = await fetch(BASE + "/leads/upload/preview", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  confirmCsv: async (file: File, mapping?: Record<string, string>): Promise<UploadResult> => {
    const fd = new FormData();
    fd.append("file", file);
    if (mapping) fd.append("mapping_json", JSON.stringify(mapping));
    const r = await fetch(BASE + "/leads/upload/confirm", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  exportUrl: (tier?: string) =>
    BASE + "/leads/export/csv" + (tier ? `?tier=${tier}` : ""),

  getIcp: () => jsonFetch<ICP>("/icp"),
  putIcp: (icp: Omit<ICP, "id" | "updated_at">) =>
    jsonFetch<ICP>("/icp", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(icp),
    }),
  getScoringConfig: () => jsonFetch<ScoringConfig>("/icp/scoring"),
  putScoringConfig: (payload: Pick<ScoringConfig, "template" | "weights">) =>
    jsonFetch<ScoringConfig>("/icp/scoring", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  runScore: (opts?: { onlyUnscored?: boolean }) =>
    jsonFetch<ScoreResult>(
      `/score${opts?.onlyUnscored ? "?only_unscored=true" : ""}`,
      { method: "POST" }
    ),
  generateEmail: (leadId: number, tone: Email["tone"] = "direct") =>
    jsonFetch<Email>(`/outreach/${leadId}?tone=${tone}`, { method: "POST" }),
  outreachDrafts: (leadId: number) => jsonFetch<Email[]>(`/outreach/${leadId}/drafts`),
};
