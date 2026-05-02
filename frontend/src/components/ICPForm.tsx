import { useState } from "react";
import type { ICP } from "../types";

interface Props {
  icp: ICP;
  onSave: (icp: Omit<ICP, "id" | "updated_at">) => Promise<void>;
}

export function ICPForm({ icp, onSave }: Props) {
  const [keywords, setKeywords] = useState(icp.industry_keywords);
  const [sizeMin, setSizeMin] = useState(icp.size_min);
  const [sizeMax, setSizeMax] = useState(icp.size_max);
  const [valueProp, setValueProp] = useState(icp.value_prop);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  async function handleSave() {
    setSaving(true);
    try {
      await onSave({
        industry_keywords: keywords,
        size_min: Number(sizeMin) || 0,
        size_max: Number(sizeMax) || 10000,
        value_prop: valueProp,
      });
      setSavedAt(new Date());
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Your ideal customer profile
        </h2>
        <span className="text-xs text-slate-400">
          drives every score below
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block text-sm">
          <span className="text-slate-600 font-medium">Industry keywords</span>
          <input
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="saas, marketing, b2b"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-200 outline-none"
          />
          <span className="text-xs text-slate-400">comma-separated</span>
        </label>

        <label className="block text-sm">
          <span className="text-slate-600 font-medium">Target size band</span>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <input
              type="number"
              value={sizeMin}
              onChange={(e) => setSizeMin(Number(e.target.value))}
              className="flex-1 min-w-[80px] rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
            />
            <span className="text-slate-400 text-xs whitespace-nowrap">to</span>
            <input
              type="number"
              value={sizeMax}
              onChange={(e) => setSizeMax(Number(e.target.value))}
              className="flex-1 min-w-[80px] rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
            />
            <span className="text-xs text-slate-500 whitespace-nowrap">employees</span>
          </div>
        </label>

        <label className="block text-sm md:col-span-2">
          <span className="text-slate-600 font-medium">What you sell</span>
          <input
            value={valueProp}
            onChange={(e) => setValueProp(e.target.value)}
            placeholder="AI-powered lead enrichment for B2B sales teams"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-indigo-400 focus:ring-1 focus:ring-indigo-200 outline-none"
          />
        </label>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-slate-400">
          {savedAt
            ? `Saved ${savedAt.toLocaleTimeString()} — re-run scoring to apply`
            : "Edit and save before running scoring."}
        </span>
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-slate-900 text-white px-4 py-2 text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save ICP"}
        </button>
      </div>
    </div>
  );
}
