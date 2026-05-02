import { useRef, useState } from "react";
import { Upload, Sparkles, RotateCcw } from "lucide-react";
import type { UploadResult } from "../types";

interface Props {
  onUpload: (file: File) => Promise<UploadResult>;
  onSeed: () => Promise<UploadResult>;
  onReset: () => Promise<void>;
  totalLeads: number;
}

export function UploadPanel({ onUpload, onSeed, onReset, totalLeads }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [mappingNote, setMappingNote] = useState<{
    source: string;
    pairs: Array<[string, string]>;
  } | null>(null);

  async function handleFile(f: File) {
    setBusy(true);
    setMsg(null);
    setMappingNote(null);
    try {
      const r = await onUpload(f);
      setMsg(
        `Uploaded ${r.inserted} new leads (${r.duplicates} duplicates, ${r.invalid} invalid). ${r.total_leads} total.`
      );
      const pairs = Object.entries(r.mapping_used || {});
      if (pairs.length > 0) {
        setMappingNote({ source: r.mapping_source, pairs });
      }
    } catch (e: any) {
      setMsg(`Error: ${e.message ?? e}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleSeed() {
    setBusy(true);
    setMsg(null);
    setMappingNote(null);
    try {
      const r = await onSeed();
      setMsg(`Loaded ${r.inserted} demo leads (${r.duplicates} dedup'd). ${r.total_leads} total.`);
    } finally {
      setBusy(false);
    }
  }

  async function handleReset() {
    if (!confirm("Clear all leads, enrichment, and scores?")) return;
    setBusy(true);
    setMsg(null);
    setMappingNote(null);
    try {
      await onReset();
      setMsg("Cleared.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Leads
        </h2>
        <span className="text-xs text-slate-400">{totalLeads} in pipeline</span>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
        >
          <Upload size={14} /> Upload CSV
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
            e.target.value = "";
          }}
        />

        <button
          onClick={handleSeed}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 text-white px-3 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
        >
          <Sparkles size={14} /> Load 50-lead demo set
        </button>

        {totalLeads > 0 && (
          <button
            onClick={handleReset}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-500 hover:bg-slate-50 disabled:opacity-50"
          >
            <RotateCcw size={14} /> Reset
          </button>
        )}
      </div>

      <p className="mt-3 text-xs text-slate-500">
        CSV must include a <code>company_name</code> column. Optional:{" "}
        <code>website</code>, <code>industry</code>, <code>employee_count</code>,{" "}
        <code>location</code>. Duplicates are collapsed by domain.
      </p>

      {msg && (
        <p className="mt-2 text-xs text-slate-600 bg-slate-50 rounded px-2 py-1.5 border border-slate-100">
          {msg}
        </p>
      )}

      {mappingNote && (
        <div className="mt-2 text-xs bg-emerald-50 border border-emerald-200 rounded px-2 py-1.5 text-emerald-800">
          <div className="font-medium mb-0.5">
            {mappingNote.source === "openai"
              ? "Auto-mapped via OpenAI:"
              : "Auto-mapped columns:"}
          </div>
          <ul className="space-y-0.5">
            {mappingNote.pairs.map(([from, to]) => (
              <li key={from} className="font-mono">
                <span className="text-emerald-900">{from}</span>{" "}
                <span className="text-emerald-500">→</span>{" "}
                <span className="text-emerald-700">{to}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
