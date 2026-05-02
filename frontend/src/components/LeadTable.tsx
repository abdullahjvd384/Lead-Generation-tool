import { useMemo, useState } from "react";
import { ArrowUpDown, ExternalLink } from "lucide-react";
import type { Lead } from "../types";
import { TierBadge } from "./TierBadge";

interface Props {
  leads: Lead[];
  selectedId: number | null;
  onSelect: (lead: Lead) => void;
}

type SortKey = "score" | "company" | "size";
type Filter = "all" | "A" | "B" | "C" | "prioritize" | "research" | "unscored";

const actionStyles: Record<string, string> = {
  Prioritize: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Research: "bg-sky-50 text-sky-700 border-sky-200",
  Nurture: "bg-amber-50 text-amber-700 border-amber-200",
  Disqualify: "bg-rose-50 text-rose-700 border-rose-200",
  "Score first": "bg-slate-50 text-slate-600 border-slate-200",
};

export function LeadTable({ leads, selectedId, onSelect }: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    let rows = leads;
    if (filter === "A" || filter === "B" || filter === "C") {
      rows = rows.filter((l) => l.tier === filter);
    } else if (filter === "prioritize") {
      rows = rows.filter((l) => l.quality?.recommended_action === "Prioritize");
    } else if (filter === "research") {
      rows = rows.filter((l) => l.quality?.recommended_action === "Research");
    } else if (filter === "unscored") {
      rows = rows.filter((l) => l.score === null);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(
        (l) =>
          l.company_name.toLowerCase().includes(q) ||
          (l.industry || "").toLowerCase().includes(q) ||
          (l.domain || "").includes(q) ||
          (l.quality?.recommended_action || "").toLowerCase().includes(q)
      );
    }
    const sorted = [...rows];
    if (sortKey === "score") {
      sorted.sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
    } else if (sortKey === "company") {
      sorted.sort((a, b) => a.company_name.localeCompare(b.company_name));
    } else {
      sorted.sort((a, b) => (b.employee_count || 0) - (a.employee_count || 0));
    }
    return sorted;
  }, [leads, filter, sortKey, search]);

  const counts = useMemo(() => {
    return {
      A: leads.filter((l) => l.tier === "A").length,
      B: leads.filter((l) => l.tier === "B").length,
      C: leads.filter((l) => l.tier === "C").length,
      prioritize: leads.filter((l) => l.quality?.recommended_action === "Prioritize").length,
      research: leads.filter((l) => l.quality?.recommended_action === "Research").length,
      unscored: leads.filter((l) => l.score === null).length,
    };
  }, [leads]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 flex flex-wrap items-center gap-2 justify-between">
        <div className="flex items-center gap-1 text-xs">
          {(["all", "prioritize", "research", "A", "B", "C", "unscored"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2.5 py-1 rounded-md font-medium transition ${
                filter === f
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {f === "all"
                ? `All (${leads.length})`
                : f === "prioritize"
                ? `Prioritize (${counts.prioritize})`
                : f === "research"
                ? `Research (${counts.research})`
                : f === "unscored"
                ? `Unscored (${counts.unscored})`
                : `Tier ${f} (${counts[f as "A" | "B" | "C"]})`}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search company, industry, domain…"
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs w-64 outline-none focus:border-indigo-400"
          />
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className="rounded-lg border border-slate-200 px-2 py-1.5 text-xs outline-none focus:border-indigo-400"
          >
            <option value="score">Sort: score ↓</option>
            <option value="company">Sort: company A→Z</option>
            <option value="size">Sort: size ↓</option>
          </select>
        </div>
      </div>

      <div className="overflow-auto max-h-[60vh]">
        <table className="w-full text-sm">
          <thead className="text-xs uppercase text-slate-500 bg-slate-50 sticky top-0">
            <tr>
              <th className="text-left px-4 py-2 w-16">Tier</th>
              <th className="text-left px-2 py-2 w-20">
                <span className="inline-flex items-center gap-1">
                  Score <ArrowUpDown size={11} />
                </span>
              </th>
              <th className="text-left px-2 py-2">Company</th>
              <th className="text-left px-2 py-2 hidden lg:table-cell">Action</th>
              <th className="text-left px-2 py-2 hidden md:table-cell">Industry</th>
              <th className="text-left px-2 py-2 w-20 hidden md:table-cell">Size</th>
              <th className="text-left px-2 py-2 hidden lg:table-cell">Why</th>
              <th className="text-left px-2 py-2 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="text-center py-12 text-slate-400 text-sm">
                  No leads match the current filter.
                </td>
              </tr>
            )}
            {filtered.map((l) => (
              <tr
                key={l.id}
                onClick={() => onSelect(l)}
                className={`cursor-pointer border-t border-slate-100 hover:bg-slate-50 ${
                  selectedId === l.id ? "bg-indigo-50/50" : ""
                }`}
              >
                <td className="px-4 py-2.5">
                  <TierBadge tier={l.tier} />
                </td>
                <td className="px-2 py-2.5 font-mono text-xs text-slate-700">
                  {l.score !== null ? l.score.toFixed(0) : "—"}
                </td>
                <td className="px-2 py-2.5">
                  <div className="font-medium text-slate-900">{l.company_name}</div>
                  <div className="text-xs text-slate-400">{l.domain}</div>
                </td>
                <td className="px-2 py-2.5 hidden lg:table-cell">
                  <span
                    className={`inline-flex rounded-md border px-2 py-0.5 text-[11px] font-medium ${
                      actionStyles[l.quality?.recommended_action || "Score first"]
                    }`}
                  >
                    {l.quality?.recommended_action || "Score first"} - {l.quality?.confidence ?? 0}%
                  </span>
                </td>
                <td className="px-2 py-2.5 text-slate-600 hidden md:table-cell">
                  {l.industry || <span className="text-slate-300">—</span>}
                </td>
                <td className="px-2 py-2.5 text-slate-600 hidden md:table-cell">
                  {l.employee_count ? l.employee_count.toLocaleString() : "—"}
                </td>
                <td className="px-2 py-2.5 text-xs text-slate-500 hidden lg:table-cell">
                  <div className="line-clamp-2 max-w-md">
                    {l.why || <span className="text-slate-300">Not yet scored</span>}
                  </div>
                </td>
                <td className="px-2 py-2.5">
                  {l.website && (
                    <a
                      href={l.website}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-slate-400 hover:text-indigo-600"
                    >
                      <ExternalLink size={14} />
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
