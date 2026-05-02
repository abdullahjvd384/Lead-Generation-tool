import { useEffect, useState } from "react";
import { Check, Copy, Download, Globe, Linkedin, Mail, Phone, X } from "lucide-react";
import type {
  Email,
  Lead,
  LookalikeList,
  PipelineStage,
  PipelineStageHistoryItem,
  ScoreHistoryItem,
} from "../types";
import { api } from "../api";
import { TierBadge } from "./TierBadge";

interface Props {
  lead: Lead | null;
  onClose: () => void;
  onUpdated?: () => void | Promise<void>;
}

const actionStyles: Record<string, string> = {
  Prioritize: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Research: "bg-sky-50 text-sky-700 border-sky-200",
  Nurture: "bg-amber-50 text-amber-700 border-amber-200",
  Disqualify: "bg-rose-50 text-rose-700 border-rose-200",
  "Score first": "bg-slate-50 text-slate-600 border-slate-200",
};

export function LeadDrawer({ lead, onClose, onUpdated }: Props) {
  const [email, setEmail] = useState<Email | null>(null);
  const [drafts, setDrafts] = useState<Email[]>([]);
  const [tone, setTone] = useState<Email["tone"]>("direct");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [stage, setStage] = useState<PipelineStage["stage"]>("new");
  const [stageReason, setStageReason] = useState("");
  const [stageBusy, setStageBusy] = useState(false);
  const [stageHistory, setStageHistory] = useState<PipelineStageHistoryItem[]>([]);
  const [scoreHistory, setScoreHistory] = useState<ScoreHistoryItem[]>([]);
  const [lookalikes, setLookalikes] = useState<LookalikeList | null>(null);
  const [lookalikeBusy, setLookalikeBusy] = useState(false);

  useEffect(() => {
    setEmail(null);
    setDrafts([]);
    setCopied(false);
    setLookalikes(null);
    setStageHistory([]);
    setScoreHistory([]);
  }, [lead?.id]);

  useEffect(() => {
    if (!lead) return;
    setStage(lead.stage ?? "new");
    setStageReason(lead.stage_reason ?? "");
    api.leadStageHistory(lead.id).then(setStageHistory);
    api.leadScoreHistory(lead.id).then(setScoreHistory);
    api.outreachDrafts(lead.id).then(setDrafts);
  }, [lead?.id, lead?.stage, lead?.stage_reason]);

  if (!lead) return null;
  const activeLead = lead;

  const contacts = activeLead.contacts ?? {};
  const signals = activeLead.signals ?? {};
  const quality = activeLead.quality ?? {
    recommended_action: "Score first",
    confidence: 0,
    risk_flags: [],
    missing_data: [],
    contact_channels: [],
    summary: "Score this lead to decide fit.",
  };

  async function saveStage(nextStage = stage, reason = stageReason) {
    setStageBusy(true);
    try {
      await api.updateLeadStage(activeLead.id, {
        stage: nextStage,
        reason,
        updated_by: "user",
      });
      await onUpdated?.();
      setStageHistory(await api.leadStageHistory(activeLead.id));
    } finally {
      setStageBusy(false);
    }
  }

  async function generate() {
    setBusy(true);
    try {
      const draft = await api.generateEmail(activeLead.id, tone);
      setEmail(draft);
      setDrafts((current) => [draft, ...current]);
    } finally {
      setBusy(false);
    }
  }

  async function copyDraft(markContacted = false) {
    if (!email) return;
    await navigator.clipboard.writeText(`Subject: ${email.subject}\n\n${email.body}`);
    setCopied(true);
    if (markContacted && activeLead.stage !== "contacted") {
      await saveStage("contacted", "Outreach copied");
    }
    setTimeout(() => setCopied(false), 1500);
  }

  async function copySequence() {
    const text = drafts
      .slice(0, 3)
      .map((draft, index) => `Step ${index + 1} (${draft.tone})\nSubject: ${draft.subject}\n\n${draft.body}`)
      .join("\n\n---\n\n");
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    if (activeLead.stage !== "contacted") {
      await saveStage("contacted", "Outreach sequence copied");
    }
    setTimeout(() => setCopied(false), 1500);
  }

  async function findLookalikes() {
    setLookalikeBusy(true);
    try {
      setLookalikes(await api.lookalikes(activeLead.id, 20));
    } finally {
      setLookalikeBusy(false);
    }
  }

  function exportLookalikes() {
    if (!lookalikes) return;
    const header = ["company", "website", "industry", "score", "similarity", "reason"];
    const rows = lookalikes.items.map((item) => [
      item.lead.company_name,
      item.lead.website,
      item.lead.industry,
      item.lead.score ?? "",
      item.similarity,
      item.reasons
        .filter((reason) => reason.contribution > 0)
        .slice(0, 3)
        .map((reason) => `${reason.signal}: ${reason.details.join(" ")}`)
        .join("; "),
    ]);
    const csv = [header, ...rows]
      .map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeLead.company_name}-lookalikes.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <div className="fixed inset-0 z-30 bg-slate-900/30" onClick={onClose} />
      <aside className="fixed bottom-0 right-0 top-0 z-40 w-full overflow-auto bg-white shadow-2xl md:w-[520px]">
        <header className="sticky top-0 flex items-start justify-between border-b border-slate-200 bg-white px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <TierBadge tier={lead.tier} />
              <h3 className="text-lg font-semibold text-slate-900">{lead.company_name}</h3>
            </div>
            <div className="mt-0.5 text-xs text-slate-400">
              {lead.domain} · {lead.industry || "-"} ·{" "}
              {lead.employee_count ? `${lead.employee_count.toLocaleString()} emp` : "size unknown"}
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-700">
            <X size={18} />
          </button>
        </header>

        <div className="space-y-5 p-5">
          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Sales action
            </h4>
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex rounded-md border px-2.5 py-1 text-xs font-semibold ${
                  actionStyles[quality.recommended_action] ?? actionStyles["Score first"]
                }`}
              >
                {quality.recommended_action}
              </span>
              <span className="text-xs text-slate-500">{quality.confidence}% data confidence</span>
            </div>
            <p className="mt-2 text-sm text-slate-700">{quality.summary}</p>
            {quality.risk_flags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {quality.risk_flags.map((flag) => (
                  <span key={flag} className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                    {flag}
                  </span>
                ))}
              </div>
            )}
          </section>

          <section className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Pipeline stage
              </h4>
              <button
                onClick={() => saveStage()}
                disabled={stageBusy}
                className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {stageBusy ? "Saving..." : "Save stage"}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <select
                value={stage}
                onChange={(event) => setStage(event.target.value as PipelineStage["stage"])}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 outline-none focus:border-indigo-400"
              >
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="qualified">Qualified</option>
                <option value="dead">Dead</option>
              </select>
              <input
                value={stageReason}
                onChange={(event) => setStageReason(event.target.value)}
                placeholder="Reason for change"
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 outline-none focus:border-indigo-400"
              />
            </div>
            <div className="text-xs text-slate-500">
              Current: <span className="font-medium capitalize text-slate-700">{lead.stage}</span>
              {lead.stage_reason ? <span> · {lead.stage_reason}</span> : null}
            </div>
            {stageHistory.length > 0 && (
              <div className="space-y-1 border-t border-slate-200 pt-2">
                {stageHistory.slice(0, 4).map((row) => (
                  <div key={row.id} className="text-xs text-slate-500">
                    <span className="capitalize">{row.from_stage}</span> {"->"}{" "}
                    <span className="capitalize text-slate-700">{row.to_stage}</span>
                    {row.reason ? ` · ${row.reason}` : ""}
                  </div>
                ))}
              </div>
            )}
          </section>

          {lead.score !== null && (
            <section>
              <div className="mb-2 flex items-baseline justify-between">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Score breakdown
                </h4>
                <span className="text-2xl font-bold text-slate-900">
                  {lead.score.toFixed(0)}
                  <span className="text-sm font-normal text-slate-400">/100</span>
                </span>
              </div>
              <p className="text-sm italic text-slate-700">{lead.why}</p>
              <div className="mt-3 space-y-1.5">
                {lead.reasons.map((reason) => (
                  <div key={reason.signal} className="text-xs">
                    <div className="mb-0.5 flex items-baseline justify-between">
                      <span className="text-slate-600">{reason.signal.replace(/_/g, " ")}</span>
                      <span className="font-mono text-slate-500">
                        {reason.contribution.toFixed(1)} / {reason.weight}
                      </span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded bg-slate-100">
                      <div
                        className="h-full bg-indigo-500"
                        style={{ width: `${Math.min(100, (reason.contribution / reason.weight) * 100)}%` }}
                      />
                    </div>
                    {reason.details.length > 0 && (
                      <div className="mt-0.5 text-[11px] text-slate-400">{reason.details.join(", ")}</div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {scoreHistory.length > 0 && (
            <section>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Score history
              </h4>
              <div className="space-y-2">
                {scoreHistory.slice(0, 3).map((row) => (
                  <div key={row.id} className="rounded-lg border border-slate-200 px-3 py-2 text-xs">
                    <div className="flex items-center justify-between text-slate-600">
                      <span>Version {row.version}</span>
                      <span>{new Date(row.changed_at).toLocaleString()}</span>
                    </div>
                    <div className="mt-1 font-medium text-slate-800">
                      {row.previous_score === null
                        ? `Initial score ${row.new_score.toFixed(0)} (${row.new_tier})`
                        : `${row.previous_score.toFixed(0)} (${row.previous_tier}) -> ${row.new_score.toFixed(0)} (${row.new_tier})`}
                    </div>
                    {row.previous_why && row.previous_why !== row.new_why && (
                      <p className="mt-1 line-clamp-2 text-slate-500">{row.new_why}</p>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          <section>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Lookalikes
              </h4>
              <div className="flex items-center gap-1.5">
                {lookalikes && (
                  <button
                    onClick={exportLookalikes}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    <Download size={12} /> Export
                  </button>
                )}
                <button
                  onClick={findLookalikes}
                  disabled={lookalikeBusy}
                  className="rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {lookalikeBusy ? "Finding..." : "Find 20 more like this"}
                </button>
              </div>
            </div>
            {lookalikes ? (
              <div className="space-y-2">
                {lookalikes.items.map((item) => (
                  <div key={item.lead.id} className="rounded-lg border border-slate-200 px-3 py-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-medium text-slate-900">{item.lead.company_name}</div>
                      <div className="text-xs text-slate-500">{item.similarity.toFixed(1)}</div>
                    </div>
                    <div className="mt-0.5 text-xs text-slate-500">
                      {item.reasons
                        .filter((reason) => reason.contribution > 0)
                        .slice(0, 2)
                        .map((reason) => `${reason.signal.replace(/_/g, " ")} ${reason.details.join(", ")}`)
                        .join(" · ") || "similar profile"}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">Run similarity search to surface related prospects.</p>
            )}
          </section>

          {lead.title && (
            <section>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Site enrichment
              </h4>
              <p className="text-sm font-medium text-slate-800">{lead.title}</p>
              {lead.description && <p className="mt-1 text-xs text-slate-500">{lead.description}</p>}
              {lead.tech_stack.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {lead.tech_stack.map((tech) => (
                    <span key={tech} className="rounded bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                      {tech}
                    </span>
                  ))}
                </div>
              )}
              {(signals.hiring || signals.founded_year) && (
                <div className="mt-2 space-x-3 text-xs text-slate-500">
                  {signals.hiring && <span>public hiring page</span>}
                  {signals.founded_year && <span>founded {signals.founded_year}</span>}
                </div>
              )}
            </section>
          )}

          {(contacts.emails?.length || contacts.phones?.length || contacts.social?.linkedin) && (
            <section>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Contacts
              </h4>
              <div className="space-y-1 text-sm">
                {contacts.emails?.slice(0, 3).map((address) => (
                  <div key={address} className="flex items-center gap-2 text-slate-700">
                    <Mail size={13} className="text-slate-400" /> {address}
                  </div>
                ))}
                {contacts.phones?.slice(0, 2).map((phone) => (
                  <div key={phone} className="flex items-center gap-2 text-slate-700">
                    <Phone size={13} className="text-slate-400" /> {phone}
                  </div>
                ))}
                {contacts.social?.linkedin && (
                  <a
                    href={contacts.social.linkedin}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 text-indigo-600 hover:underline"
                  >
                    <Linkedin size={13} /> LinkedIn
                  </a>
                )}
                {lead.website && (
                  <a
                    href={lead.website}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-2 text-indigo-600 hover:underline"
                  >
                    <Globe size={13} /> {lead.website}
                  </a>
                )}
              </div>
            </section>
          )}

          <section>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Outreach drafts
              </h4>
              <div className="flex items-center gap-1.5">
                {drafts.length > 1 && (
                  <button
                    onClick={copySequence}
                    className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-indigo-600"
                  >
                    <Copy size={12} /> Sequence
                  </button>
                )}
                {email && (
                  <button
                    onClick={() => copyDraft(true)}
                    className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-indigo-600"
                  >
                    {copied ? <Check size={12} /> : <Copy size={12} />}
                    {copied ? "Copied" : "Copy + contacted"}
                  </button>
                )}
              </div>
            </div>
            <div className="mb-2 flex gap-2 text-xs">
              {(["direct", "warm", "executive"] as Email["tone"][]).map((option) => (
                <button
                  key={option}
                  onClick={() => setTone(option)}
                  className={`rounded-md px-2 py-1 font-medium capitalize ${
                    tone === option ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
            {!email ? (
              <button
                onClick={generate}
                disabled={busy}
                className="w-full rounded-lg bg-slate-900 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {busy ? "Generating..." : "Generate personalized email"}
              </button>
            ) : (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                <div className="mb-2 font-medium text-slate-900">{email.subject}</div>
                <div className="whitespace-pre-line leading-relaxed text-slate-700">{email.body}</div>
                <button onClick={generate} className="mt-3 text-xs text-slate-500 hover:text-indigo-600">
                  Regenerate in {tone} tone
                </button>
              </div>
            )}
            {drafts.length > 0 && (
              <div className="mt-3 space-y-1">
                {drafts.slice(0, 3).map((draft) => (
                  <button
                    key={`${draft.id ?? draft.subject}-${draft.created_at ?? ""}`}
                    onClick={() => setEmail(draft)}
                    className="w-full rounded-md border border-slate-200 px-3 py-2 text-left text-xs hover:bg-slate-50"
                  >
                    <span className="font-medium capitalize text-slate-700">{draft.tone}</span>
                    <span className="text-slate-400"> · {draft.subject}</span>
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>
      </aside>
    </>
  );
}
