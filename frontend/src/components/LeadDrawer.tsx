import { useEffect, useState } from "react";
import { Mail, X, Copy, Check, Globe, Phone, Linkedin } from "lucide-react";
import type { Email, Lead } from "../types";
import { TierBadge } from "./TierBadge";
import { api } from "../api";

interface Props {
  lead: Lead | null;
  onClose: () => void;
}

export function LeadDrawer({ lead, onClose }: Props) {
  const [email, setEmail] = useState<Email | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setEmail(null);
    setCopied(false);
  }, [lead?.id]);

  if (!lead) return null;

  async function generate() {
    if (!lead) return;
    setBusy(true);
    try {
      const e = await api.generateEmail(lead.id);
      setEmail(e);
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    if (!email) return;
    await navigator.clipboard.writeText(`Subject: ${email.subject}\n\n${email.body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const contacts = lead.contacts ?? {};
  const signals = lead.signals ?? {};

  return (
    <>
      <div
        className="fixed inset-0 bg-slate-900/30 z-30"
        onClick={onClose}
      />
      <aside className="fixed right-0 top-0 bottom-0 w-full md:w-[480px] bg-white shadow-2xl z-40 overflow-auto">
        <header className="px-5 py-4 border-b border-slate-200 flex items-start justify-between sticky top-0 bg-white">
          <div>
            <div className="flex items-center gap-2">
              <TierBadge tier={lead.tier} />
              <h3 className="text-lg font-semibold text-slate-900">
                {lead.company_name}
              </h3>
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              {lead.domain} · {lead.industry || "—"} ·{" "}
              {lead.employee_count ? `${lead.employee_count.toLocaleString()} emp` : "size unknown"}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-700"
          >
            <X size={18} />
          </button>
        </header>

        <div className="p-5 space-y-5">
          {lead.score !== null && (
            <section>
              <div className="flex items-baseline justify-between mb-2">
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Score breakdown
                </h4>
                <span className="text-2xl font-bold text-slate-900">
                  {lead.score.toFixed(0)}
                  <span className="text-sm text-slate-400 font-normal">/100</span>
                </span>
              </div>
              <p className="text-sm text-slate-700 italic">{lead.why}</p>
              <div className="mt-3 space-y-1.5">
                {lead.reasons.map((r) => (
                  <div key={r.signal} className="text-xs">
                    <div className="flex items-baseline justify-between mb-0.5">
                      <span className="text-slate-600">
                        {r.signal.replace(/_/g, " ")}
                      </span>
                      <span className="font-mono text-slate-500">
                        {r.contribution.toFixed(1)} / {r.weight}
                      </span>
                    </div>
                    <div className="h-1.5 rounded bg-slate-100 overflow-hidden">
                      <div
                        className="h-full bg-indigo-500"
                        style={{ width: `${(r.contribution / r.weight) * 100}%` }}
                      />
                    </div>
                    {r.details.length > 0 && (
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        {r.details.join(", ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {lead.title && (
            <section>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Site enrichment
              </h4>
              <p className="text-sm font-medium text-slate-800">{lead.title}</p>
              {lead.description && (
                <p className="text-xs text-slate-500 mt-1">{lead.description}</p>
              )}
              {lead.tech_stack.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {lead.tech_stack.map((t) => (
                    <span
                      key={t}
                      className="text-[11px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
              {(signals.hiring || signals.founded_year) && (
                <div className="mt-2 text-xs text-slate-500 space-x-3">
                  {signals.hiring && <span>· public hiring page</span>}
                  {signals.founded_year && <span>· founded {signals.founded_year}</span>}
                </div>
              )}
            </section>
          )}

          {(contacts.emails?.length || contacts.phones?.length || contacts.social?.linkedin) && (
            <section>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Contacts
              </h4>
              <div className="space-y-1 text-sm">
                {contacts.emails?.slice(0, 3).map((e) => (
                  <div key={e} className="flex items-center gap-2 text-slate-700">
                    <Mail size={13} className="text-slate-400" /> {e}
                  </div>
                ))}
                {contacts.phones?.slice(0, 2).map((p) => (
                  <div key={p} className="flex items-center gap-2 text-slate-700">
                    <Phone size={13} className="text-slate-400" /> {p}
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
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                Outreach draft
              </h4>
              {email && (
                <button
                  onClick={copy}
                  className="text-xs inline-flex items-center gap-1 text-slate-500 hover:text-indigo-600"
                >
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  {copied ? "Copied" : "Copy"}
                </button>
              )}
            </div>
            {!email ? (
              <button
                onClick={generate}
                disabled={busy}
                className="w-full rounded-lg bg-slate-900 text-white py-2.5 text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
              >
                {busy ? "Generating…" : "Generate personalized email"}
              </button>
            ) : (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                <div className="font-medium text-slate-900 mb-2">
                  {email.subject}
                </div>
                <div className="whitespace-pre-line text-slate-700 leading-relaxed">
                  {email.body}
                </div>
                <button
                  onClick={generate}
                  className="mt-3 text-xs text-slate-500 hover:text-indigo-600"
                >
                  Regenerate
                </button>
              </div>
            )}
          </section>
        </div>
      </aside>
    </>
  );
}
