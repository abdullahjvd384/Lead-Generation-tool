import { useRef, useState } from "react";
import { Check, RotateCcw, Sparkles, Upload, X } from "lucide-react";
import type { CsvPreview, UploadResult } from "../types";

interface Props {
  onPreview: (file: File, mapping?: Record<string, string>) => Promise<CsvPreview>;
  onConfirm: (file: File, mapping?: Record<string, string>) => Promise<UploadResult>;
  onSeed: () => Promise<UploadResult>;
  onReset: () => Promise<void>;
  totalLeads: number;
}

const targets = ["company_name", "website", "industry", "employee_count", "location", "skip"];

export function UploadPanel({ onPreview, onConfirm, onSeed, onReset, totalLeads }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});

  async function handleFile(nextFile: File) {
    setBusy(true);
    setMsg(null);
    try {
      const result = await onPreview(nextFile);
      setFile(nextFile);
      setPreview(result);
      const detected: Record<string, string> = {};
      for (const [from, to] of Object.entries(result.mapping_used || {})) detected[from] = to;
      for (const col of result.columns) {
        if (!detected[col]) detected[col] = result.canonical_columns.includes(col) ? col : "skip";
      }
      setMapping(detected);
    } catch (e: any) {
      setMsg(`Error: ${e.message ?? e}`);
    } finally {
      setBusy(false);
    }
  }

  async function refreshPreview(nextMapping = mapping) {
    if (!file) return;
    setBusy(true);
    try {
      setPreview(await onPreview(file, nextMapping));
    } catch (e: any) {
      setMsg(`Error: ${e.message ?? e}`);
    } finally {
      setBusy(false);
    }
  }

  async function confirmUpload() {
    if (!file) return;
    setBusy(true);
    setMsg(null);
    try {
      const result = await onConfirm(file, mapping);
      setMsg(
        `Imported ${result.inserted} new leads (${result.duplicates} duplicates, ${result.invalid} invalid). ${result.total_leads} total.`
      );
      setFile(null);
      setPreview(null);
      setMapping({});
    } catch (e: any) {
      setMsg(`Error: ${e.message ?? e}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleSeed() {
    setBusy(true);
    setMsg(null);
    try {
      const result = await onSeed();
      setMsg(`Loaded ${result.inserted} demo leads (${result.duplicates} duplicates). ${result.total_leads} total.`);
    } finally {
      setBusy(false);
    }
  }

  async function handleReset() {
    if (!confirm("Clear all leads, enrichment, and scores?")) return;
    setBusy(true);
    setMsg(null);
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
          <Upload size={14} /> Preview CSV
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(event) => {
            const nextFile = event.target.files?.[0];
            if (nextFile) handleFile(nextFile);
            event.target.value = "";
          }}
        />

        <button
          onClick={handleSeed}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
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
        Preview maps messy CSV headers, flags invalid rows, and confirms duplicates before import.
      </p>

      {msg && (
        <p className="mt-2 rounded border border-slate-100 bg-slate-50 px-2 py-1.5 text-xs text-slate-600">
          {msg}
        </p>
      )}

      {preview && file && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div className="max-h-[88vh] w-full max-w-4xl overflow-auto rounded-xl bg-white shadow-2xl">
            <div className="sticky top-0 flex items-start justify-between border-b border-slate-200 bg-white px-5 py-4">
              <div>
                <h3 className="text-base font-semibold text-slate-900">Confirm CSV import</h3>
                <p className="text-xs text-slate-500">{file.name} · {preview.total_rows} rows</p>
              </div>
              <button onClick={() => setPreview(null)} className="text-slate-400 hover:text-slate-700">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-5 p-5">
              <div className="grid gap-3 sm:grid-cols-4">
                <Metric label="Will import" value={preview.inserted} tone="emerald" />
                <Metric label="Duplicates" value={preview.duplicates} tone="amber" />
                <Metric label="Invalid" value={preview.invalid} tone="rose" />
                <Metric label="Mapping" value={preview.mapping_source} tone="slate" />
              </div>

              <section>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Column mapping
                </h4>
                <div className="grid gap-2 md:grid-cols-2">
                  {preview.columns.map((column) => (
                    <label key={column} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm">
                      <span className="truncate font-mono text-xs text-slate-600">{column}</span>
                      <select
                        value={mapping[column] || "skip"}
                        onChange={(event) => {
                          const next = { ...mapping, [column]: event.target.value };
                          setMapping(next);
                          refreshPreview(next);
                        }}
                        className="rounded-md border border-slate-200 px-2 py-1 text-xs outline-none focus:border-indigo-400"
                      >
                        {targets.map((target) => (
                          <option key={target} value={target}>{target}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
              </section>

              <section>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  First rows
                </h4>
                <div className="overflow-auto rounded-lg border border-slate-200">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 text-slate-500">
                      <tr>
                        {targets.slice(0, 5).map((target) => (
                          <th key={target} className="px-3 py-2 text-left">{target}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.preview_rows.map((row, index) => (
                        <tr key={index} className="border-t border-slate-100">
                          {targets.slice(0, 5).map((target) => (
                            <td key={target} className="max-w-52 truncate px-3 py-2 text-slate-600">
                              {String(row[target] ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <div className="flex items-center justify-between gap-3">
                <span className="text-xs text-slate-400">
                  {preview.invalid_rows.length > 0
                    ? `Invalid CSV rows: ${preview.invalid_rows.join(", ")}`
                    : "No invalid rows detected."}
                </span>
                <button
                  onClick={confirmUpload}
                  disabled={busy || !Object.values(mapping).includes("company_name")}
                  className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  <Check size={14} /> Confirm import
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number | string; tone: string }) {
  const cls =
    tone === "emerald"
      ? "text-emerald-700 bg-emerald-50 border-emerald-200"
      : tone === "amber"
      ? "text-amber-700 bg-amber-50 border-amber-200"
      : tone === "rose"
      ? "text-rose-700 bg-rose-50 border-rose-200"
      : "text-slate-700 bg-slate-50 border-slate-200";
  return (
    <div className={`rounded-lg border px-3 py-3 ${cls}`}>
      <div className="text-xs font-medium">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}
