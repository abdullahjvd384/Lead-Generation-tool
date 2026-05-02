import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, CircleHelp, MailWarning, Search } from "lucide-react";
import type { Lead } from "../types";
import { TierBadge } from "./TierBadge";

interface Props {
  leads: Lead[];
  onSelect: (lead: Lead) => void;
}

type QueueTab = "ready" | "research" | "missing" | "low" | "unscored";

const tabs: Array<{ id: QueueTab; label: string; icon: typeof CheckCircle2 }> = [
  { id: "ready", label: "Ready Now", icon: CheckCircle2 },
  { id: "research", label: "Needs Research", icon: Search },
  { id: "missing", label: "Missing Contact", icon: MailWarning },
  { id: "low", label: "Low ICP Fit", icon: AlertTriangle },
  { id: "unscored", label: "Unscored", icon: CircleHelp },
];

export function ActionQueue({ leads, onSelect }: Props) {
  const [active, setActive] = useState<QueueTab>("ready");

  const groups = useMemo(() => {
    const hasNoContact = (lead: Lead) => (lead.quality?.contact_channels?.length ?? 0) === 0;
    return {
      ready: leads.filter((lead) => lead.quality?.recommended_action === "Prioritize"),
      research: leads.filter((lead) => lead.quality?.recommended_action === "Research"),
      missing: leads.filter((lead) => lead.score !== null && hasNoContact(lead)),
      low: leads.filter(
        (lead) =>
          lead.quality?.recommended_action === "Disqualify" ||
          lead.tier === "C" ||
          lead.quality?.risk_flags?.includes("weak ICP keyword match")
      ),
      unscored: leads.filter((lead) => lead.score === null),
    } satisfies Record<QueueTab, Lead[]>;
  }, [leads]);

  const rows = [...groups[active]].sort((a, b) => (b.score ?? -1) - (a.score ?? -1)).slice(0, 8);

  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Action queue
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            The daily worklist: who to contact, research, repair, suppress, or score next.
          </p>
        </div>
        <div className="flex flex-wrap gap-1 text-xs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActive(tab.id)}
                className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 font-medium transition ${
                  active === tab.id
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <Icon size={13} />
                {tab.label} ({groups[tab.id].length})
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {rows.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-400 lg:col-span-2">
            Nothing in this queue.
          </div>
        ) : (
          rows.map((lead) => (
            <button
              key={lead.id}
              onClick={() => onSelect(lead)}
              className="text-left rounded-lg border border-slate-200 px-4 py-3 hover:border-indigo-200 hover:bg-indigo-50/50 transition"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <TierBadge tier={lead.tier} />
                    <span className="truncate text-sm font-semibold text-slate-900">
                      {lead.company_name}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    {lead.quality?.summary || lead.why || "Score this lead to decide fit."}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <div className="text-sm font-semibold text-slate-900">
                    {lead.score !== null ? `${lead.score.toFixed(0)}/100` : "-"}
                  </div>
                  <div className="text-xs text-slate-400">{lead.quality?.confidence ?? 0}% conf</div>
                </div>
              </div>
              {(lead.quality?.risk_flags?.length ?? 0) > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {lead.quality.risk_flags.slice(0, 3).map((flag) => (
                    <span key={flag} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500">
                      {flag}
                    </span>
                  ))}
                </div>
              )}
            </button>
          ))
        )}
      </div>
    </section>
  );
}
