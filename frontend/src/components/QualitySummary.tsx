import { AlertTriangle, CheckCircle2, ClipboardList, Search } from "lucide-react";
import type { ReactNode } from "react";
import type { Lead } from "../types";

interface Props {
  leads: Lead[];
}

const actionStyles: Record<string, string> = {
  Prioritize: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Research: "bg-sky-50 text-sky-700 border-sky-200",
  Nurture: "bg-amber-50 text-amber-700 border-amber-200",
  Disqualify: "bg-rose-50 text-rose-700 border-rose-200",
  "Score first": "bg-slate-50 text-slate-600 border-slate-200",
};

export function QualitySummary({ leads }: Props) {
  if (leads.length === 0) return null;

  const scored = leads.filter((l) => l.score !== null);
  const avgConfidence =
    leads.reduce((sum, lead) => sum + (lead.quality?.confidence ?? 0), 0) /
    leads.length;
  const priorityLeads = leads.filter(
    (l) => l.quality?.recommended_action === "Prioritize"
  ).length;
  const researchLeads = leads.filter(
    (l) => l.quality?.recommended_action === "Research"
  ).length;
  const contactableA = leads.filter(
    (l) =>
      l.tier === "A" &&
      (l.quality?.contact_channels?.length ?? 0) > 0
  ).length;

  const riskCounts = new Map<string, number>();
  leads.forEach((lead) => {
    lead.quality?.risk_flags?.forEach((flag) => {
      riskCounts.set(flag, (riskCounts.get(flag) ?? 0) + 1);
    });
  });
  const topRisks = [...riskCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  return (
    <section className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
            Quality control
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Converts raw scores into sales actions, confidence, and cleanup work.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          {["Prioritize", "Research", "Nurture", "Disqualify", "Score first"].map(
            (action) => {
              const count = leads.filter(
                (l) => l.quality?.recommended_action === action
              ).length;
              return (
                <span
                  key={action}
                  className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 font-medium ${actionStyles[action]}`}
                >
                  {action} {count}
                </span>
              );
            }
          )}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mt-4">
        <Metric
          icon={<CheckCircle2 size={16} />}
          label="Ready now"
          value={priorityLeads.toLocaleString()}
          detail="high-fit and contactable"
        />
        <Metric
          icon={<Search size={16} />}
          label="Needs research"
          value={researchLeads.toLocaleString()}
          detail="fit signal with data gaps"
        />
        <Metric
          icon={<ClipboardList size={16} />}
          label="Contactable A-tier"
          value={contactableA.toLocaleString()}
          detail={`${scored.length} scored leads`}
        />
        <Metric
          icon={<AlertTriangle size={16} />}
          label="Avg confidence"
          value={`${Math.round(avgConfidence)}%`}
          detail={topRisks.length ? `top risk: ${topRisks[0][0]}` : "no risks found"}
        />
      </div>

      {topRisks.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
          {topRisks.map(([flag, count]) => (
            <span key={flag} className="rounded-md bg-slate-50 px-2 py-1">
              {flag}: {count}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

function Metric({
  icon,
  label,
  value,
  detail,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 px-3 py-3">
      <div className="flex items-center justify-between text-slate-500">
        <span className="text-xs font-medium">{label}</span>
        {icon}
      </div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      <div className="text-xs text-slate-400">{detail}</div>
    </div>
  );
}
