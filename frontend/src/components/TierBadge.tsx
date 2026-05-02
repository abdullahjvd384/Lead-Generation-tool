interface Props {
  tier: "A" | "B" | "C" | null;
}

const COLORS: Record<string, string> = {
  A: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  B: "bg-amber-100 text-amber-800 ring-amber-200",
  C: "bg-slate-100 text-slate-600 ring-slate-200",
  "—": "bg-slate-50 text-slate-400 ring-slate-200",
};

export function TierBadge({ tier }: Props) {
  const key = tier ?? "—";
  return (
    <span
      className={`inline-flex items-center justify-center w-7 h-6 rounded-md text-xs font-semibold ring-1 ring-inset ${COLORS[key]}`}
    >
      {key}
    </span>
  );
}
