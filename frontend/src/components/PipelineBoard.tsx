import { CheckCircle2, Flame, MailCheck, XCircle } from "lucide-react";
import type { Lead, PipelineStage } from "../types";
import { TierBadge } from "./TierBadge";

interface Props {
  leads: Lead[];
  selectedId: number | null;
  onSelect: (lead: Lead) => void;
  onStageChange: (lead: Lead, stage: PipelineStage["stage"]) => Promise<void>;
}

const columns: Array<{
  stage: PipelineStage["stage"];
  label: string;
  icon: typeof Flame;
}> = [
  { stage: "new", label: "New", icon: Flame },
  { stage: "contacted", label: "Contacted", icon: MailCheck },
  { stage: "qualified", label: "Qualified", icon: CheckCircle2 },
  { stage: "dead", label: "Dead", icon: XCircle },
];

export function PipelineBoard({ leads, selectedId, onSelect, onStageChange }: Props) {
  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Pipeline board
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Move prospects through a simple qualification workflow.
          </p>
        </div>
        <span className="text-xs text-slate-400">{leads.length} tracked</span>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-4">
        {columns.map((column) => {
          const Icon = column.icon;
          const rows = leads
            .filter((lead) => lead.stage === column.stage)
            .sort((a, b) => (b.score ?? -1) - (a.score ?? -1))
            .slice(0, 8);
          return (
            <div key={column.stage} className="rounded-lg border border-slate-200 bg-slate-50/60">
              <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
                <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-600">
                  <Icon size={13} />
                  {column.label}
                </div>
                <span className="text-xs text-slate-400">{rows.length}</span>
              </div>
              <div className="space-y-2 p-2 min-h-40">
                {rows.length === 0 ? (
                  <div className="rounded-md border border-dashed border-slate-200 px-3 py-6 text-center text-xs text-slate-400">
                    Empty
                  </div>
                ) : (
                  rows.map((lead) => (
                    <div
                      key={lead.id}
                      className={`rounded-md border bg-white px-3 py-2 ${
                        selectedId === lead.id ? "border-indigo-300" : "border-slate-200"
                      }`}
                    >
                      <button onClick={() => onSelect(lead)} className="w-full text-left">
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-medium text-slate-900">
                            {lead.company_name}
                          </span>
                          <TierBadge tier={lead.tier} />
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          {lead.score !== null ? `${lead.score.toFixed(0)}/100` : "unscored"} ·{" "}
                          {lead.quality?.recommended_action || "Score first"}
                        </div>
                      </button>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {columns
                          .filter((target) => target.stage !== column.stage)
                          .slice(0, 3)
                          .map((target) => (
                            <button
                              key={target.stage}
                              onClick={() => onStageChange(lead, target.stage)}
                              className="rounded border border-slate-200 px-1.5 py-0.5 text-[11px] text-slate-500 hover:bg-slate-50"
                            >
                              {target.label}
                            </button>
                          ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
