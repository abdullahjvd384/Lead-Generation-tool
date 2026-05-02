import { useEffect, useState } from "react";
import { Zap, Download } from "lucide-react";
import { api } from "./api";
import type { ICP, Lead } from "./types";
import { ICPForm } from "./components/ICPForm";
import { UploadPanel } from "./components/UploadPanel";
import { LeadTable } from "./components/LeadTable";
import { LeadDrawer } from "./components/LeadDrawer";

export default function App() {
  const [icp, setIcp] = useState<ICP | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selected, setSelected] = useState<Lead | null>(null);
  const [scoring, setScoring] = useState(false);
  const [scoreMsg, setScoreMsg] = useState<string | null>(null);
  const [ai, setAi] = useState<{
    gemini_enabled: boolean;
    has_key: boolean;
    circuit_open: boolean;
  } | null>(null);

  async function refreshAiStatus() {
    const s = await api.systemStatus();
    setAi({
      gemini_enabled: s.gemini_enabled,
      has_key: s.has_key,
      circuit_open: s.circuit_open,
    });
  }

  async function reloadLeads() {
    const list = await api.listLeads();
    setLeads(list);
    if (selected) {
      const fresh = list.find((l) => l.id === selected.id);
      if (fresh) setSelected(fresh);
    }
  }

  useEffect(() => {
    api.getIcp().then(setIcp);
    refreshAiStatus();
    reloadLeads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSaveIcp(payload: Omit<ICP, "id" | "updated_at">) {
    const updated = await api.putIcp(payload);
    setIcp(updated);
  }

  async function handleScore() {
    setScoring(true);
    setScoreMsg(null);
    try {
      const r = await api.runScore();
      setScoreMsg(
        `Scored ${r.scored} leads from live sites, ${r.cached} without site data, ${r.failed} unreachable.`
      );
      await Promise.all([reloadLeads(), refreshAiStatus()]);
    } finally {
      setScoring(false);
    }
  }

  const scoredCount = leads.filter((l) => l.score !== null).length;

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Zap size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-slate-900">
                Lead Qualifier
              </h1>
              <p className="text-xs text-slate-500 -mt-0.5">
                Turn 500 leads into the 20 worth calling Monday.
              </p>
            </div>
            {ai && (() => {
              const active = ai.gemini_enabled;
              const broken = ai.has_key && ai.circuit_open;
              const label = active
                ? "AI: Gemini"
                : broken
                ? "AI: rule-based (Gemini unavailable)"
                : "AI: rule-based";
              const tooltip = active
                ? "Gemini-powered scoring, email writing, and CSV mapping are active"
                : broken
                ? "Your Gemini key is set but recent calls failed (likely quota or invalid key). The app fell back to rule-based logic for the rest of this session — restart the backend to retry."
                : "Set GEMINI_API_KEY in backend/.env to enable AI features";
              const cls = active
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : broken
                ? "bg-rose-50 text-rose-700 border-rose-200"
                : "bg-amber-50 text-amber-700 border-amber-200";
              const dot = active
                ? "bg-emerald-500"
                : broken
                ? "bg-rose-500"
                : "bg-amber-500";
              return (
                <span
                  title={tooltip}
                  className={`ml-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border ${cls}`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
                  {label}
                </span>
              );
            })()}
          </div>
          <a
            href={api.exportUrl()}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm hover:bg-slate-50"
          >
            <Download size={14} /> Export CSV
          </a>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-5">
        <div className="grid gap-5 md:grid-cols-2">
          {icp && <ICPForm icp={icp} onSave={handleSaveIcp} />}
          <UploadPanel
            onUpload={async (f) => {
              const r = await api.uploadCsv(f);
              await reloadLeads();
              return r;
            }}
            onSeed={async () => {
              const r = await api.seedDemo();
              await reloadLeads();
              return r;
            }}
            onReset={async () => {
              await api.resetLeads();
              setSelected(null);
              await reloadLeads();
            }}
            totalLeads={leads.length}
          />
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Score the pipeline
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Fetches each lead's website (rate-limited, cached 7 days), scores
              against your ICP, and ranks A → C.{" "}
              {scoredCount > 0 && (
                <span className="text-slate-400">
                  Last run: {scoredCount} of {leads.length} leads scored.
                </span>
              )}
            </p>
            {scoreMsg && (
              <p className="text-xs text-emerald-700 mt-2 bg-emerald-50 inline-block px-2 py-1 rounded">
                {scoreMsg}
              </p>
            )}
          </div>
          <button
            onClick={handleScore}
            disabled={scoring || leads.length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 text-white px-4 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
          >
            <Zap size={14} />
            {scoring ? "Scoring…" : "Score all leads"}
          </button>
        </div>

        {leads.length === 0 ? (
          <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center">
            <p className="text-slate-500 text-sm">
              No leads yet — upload a CSV or click <strong>Load 50-lead demo set</strong> to start.
            </p>
          </div>
        ) : (
          <LeadTable
            leads={leads}
            selectedId={selected?.id ?? null}
            onSelect={setSelected}
          />
        )}
      </main>

      <LeadDrawer lead={selected} onClose={() => setSelected(null)} />

      <footer className="max-w-7xl mx-auto px-6 py-8 text-xs text-slate-400">
        Built for Caprae's AI-Readiness challenge. Scraping is rate-limited
        (≤5 concurrent, 1s gap per domain) and cached 7 days.
      </footer>
    </div>
  );
}
