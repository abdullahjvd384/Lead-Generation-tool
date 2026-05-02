import { useEffect, useMemo, useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { api } from "../api";
import type { ScoringConfig } from "../types";

interface Props {
  onSaved?: () => void | Promise<void>;
}

const signals = [
  ["industry_match", "Industry fit"],
  ["size_band", "Size band"],
  ["tech_relevance", "Tech relevance"],
  ["contact_completeness", "Contactability"],
  ["activity_recency", "Timing signals"],
] as const;

const templates: Record<string, Record<string, number>> = {
  Balanced: {
    industry_match: 30,
    size_band: 20,
    tech_relevance: 20,
    contact_completeness: 15,
    activity_recency: 15,
  },
  "Fit first": {
    industry_match: 45,
    size_band: 25,
    tech_relevance: 15,
    contact_completeness: 10,
    activity_recency: 5,
  },
  "Outbound ready": {
    industry_match: 25,
    size_band: 15,
    tech_relevance: 15,
    contact_completeness: 30,
    activity_recency: 15,
  },
};

export function ScoringConfigPanel({ onSaved }: Props) {
  const [config, setConfig] = useState<ScoringConfig | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>(templates.Balanced);
  const [template, setTemplate] = useState("Balanced");
  const [saving, setSaving] = useState(false);
  const total = useMemo(
    () => signals.reduce((sum, [key]) => sum + Number(weights[key] || 0), 0),
    [weights]
  );

  useEffect(() => {
    api.getScoringConfig().then((data) => {
      setConfig(data);
      setTemplate(data.template || "Balanced");
      setWeights(data.weights);
    });
  }, []);

  async function save() {
    setSaving(true);
    try {
      const updated = await api.putScoringConfig({ template, weights });
      setConfig(updated);
      setWeights(updated.weights);
      await onSaved?.();
    } finally {
      setSaving(false);
    }
  }

  function applyTemplate(name: string) {
    setTemplate(name);
    setWeights(templates[name]);
  }

  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Scoring model
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Tune how the ICP score weights fit, readiness, and timing.
          </p>
        </div>
        <div className="inline-flex items-center gap-1 text-xs text-slate-400">
          <SlidersHorizontal size={13} />
          v{config?.version ?? 1}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        {Object.keys(templates).map((name) => (
          <button
            key={name}
            onClick={() => applyTemplate(name)}
            className={`rounded-md px-2.5 py-1 font-medium ${
              template === name ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {signals.map(([key, label]) => (
          <label key={key} className="text-sm">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-600">{label}</span>
              <span className="font-mono text-slate-400">{Number(weights[key] || 0).toFixed(0)}</span>
            </div>
            <input
              type="range"
              min={0}
              max={60}
              value={weights[key] || 0}
              onChange={(event) =>
                setWeights((current) => ({ ...current, [key]: Number(event.target.value) }))
              }
              className="mt-1 w-full accent-indigo-600"
            />
          </label>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs text-slate-400">
          Total {total.toFixed(0)}. Saved weights normalize to 100 automatically.
        </span>
        <button
          onClick={save}
          disabled={saving}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save model"}
        </button>
      </div>
    </section>
  );
}
