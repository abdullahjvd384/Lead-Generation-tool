# Lead Qualifier — AI-style scoring for sales pipelines

Built for Caprae Capital's AI-Readiness Pre-Screening Challenge.

> Turn a list of 500 raw leads into the 20 worth calling Monday.

## What it does

A single-screen web app that takes a CSV of leads (or a built-in 50-row demo set), enriches each one by scraping its website, scores them against a user-defined ICP, and produces a ranked, action-ready outreach queue with per-lead personalized cold emails.

The leverage point is the layer **on top of** scraping — anyone can collect rows of contact data; the value is in *prioritization* and *first-touch readiness*. That's where this tool spends its complexity.

### End-to-end flow

1. **Define your ICP** — three fields: industry keywords, target size band, what you sell.
2. **Add leads** — upload a CSV, or click *Load 50-lead demo set* (B2B SaaS companies, ships with the repo).
3. **Score** — backend fetches each company's homepage (rate-limited, cached 7 days), extracts tech-stack signals, contacts, and activity hints, then computes a transparent 0–100 score with an A/B/C tier and a one-sentence "why."
4. **Action** — click a lead to see signal breakdown, copy-ready contact info, and a personalized 3-line cold email composed from the actual scraped facts. Export the whole pipeline to a HubSpot-shaped CSV.

## Why this design

The challenge rubric weights **Business Understanding** and **UX** above raw technicality. Two design choices follow from that:

1. **Transparent rule-based scoring, not a black-box LLM.** Every score is a sum of five named contributions (industry_match, size_band, tech_relevance, contact_completeness, activity_recency) with their weights and raw values exposed in the UI. A sales rep can *trust* a score they can audit. (LLM scoring is an obvious extension — the codebase is structured so swapping `services/scorer.py` for an LLM call would be a one-file change, with the same return shape.)
2. **Single-screen workflow.** Upload → score → review → export, no nested settings. The only modal is the per-lead drawer.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| Scraping | `httpx` (async, rate-limited) + BeautifulSoup |
| Frontend | React 18 + TypeScript + Vite + Tailwind |
| Storage | SQLite (`leadgen.db`, auto-created) — leads, ICP, enrichment, scores, scrape cache |
| Caching | 7-day scrape cache keyed by normalized domain. Re-scoring with the same ICP is essentially free. |
| Scraping politeness | ≤5 concurrent requests, 1s gap per domain, 5s timeout, custom User-Agent, graceful failure (lead still scored on metadata) |
| Tests | `pytest`, 28 unit tests covering scorer, enricher, dedupe, CSV mapper, and Gemini fallback |
| AI (optional) | Google Gemini 2.0 Flash via `google-generativeai`, with graceful fallback to rule-based logic when no key is set |

## Setup

Requires Python 3.10+ and Node 18+.

### Backend
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload   # serves on http://127.0.0.1:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                     # serves on http://127.0.0.1:5173
```

### Optional — enable Gemini AI

The app works fully without an API key (rule-based scoring + template emails). To unlock Gemini-powered scoring, email writing, and intelligent CSV column mapping:

1. Get a free key at <https://aistudio.google.com/apikey> (no credit card required)
2. Copy `backend/.env.example` to `backend/.env`
3. Set `GEMINI_API_KEY=your_key_here`
4. Restart the backend

The header in the UI shows a green **AI: Gemini** pill when Gemini is active, or an amber **AI: rule-based** pill when it's not.

Open <http://127.0.0.1:5173>. The Vite dev server proxies `/api/*` to the backend on `:8000`.

### Tests
```bash
cd backend && .venv/Scripts/python -m pytest -q
```

## Architecture

```
backend/
├── app/
│   ├── main.py             FastAPI app + CORS + dotenv; mounts five routers
│   ├── db.py               SQLAlchemy models: ICP, Lead, Enrichment, Score, ScrapeCache
│   ├── models.py           Pydantic request/response schemas
│   ├── routes/
│   │   ├── leads.py        upload (with Gemini column mapping), list, get, seed, reset, export CSV
│   │   ├── icp.py          GET/PUT singleton ICP
│   │   ├── score.py        POST /score → enrich + score (Gemini if enabled, rule-based otherwise)
│   │   ├── outreach.py     POST /outreach/{id} → personalized email (Gemini or template)
│   │   └── system.py       GET /system/status → {gemini_enabled, model}
│   ├── services/
│   │   ├── scraper.py      polite async fetch with SQLite scrape cache
│   │   ├── enricher.py     pure HTML → {title, description, tech_stack, contacts, signals}
│   │   ├── scorer.py       rule-based weighted scoring (fallback)
│   │   ├── scorer_llm.py   Gemini scorer; same return shape as scorer.score_lead
│   │   ├── outreach.py     fact-grounded template email (fallback)
│   │   ├── outreach_llm.py Gemini email writer; same {subject, body} shape
│   │   ├── csv_mapper.py   alias dict + Gemini fallback for CSV column normalization
│   │   ├── gemini.py       single SDK wrapper, throttled to 12 RPM, returns None on any error
│   │   └── dedupe.py       URL → canonical domain (the dedup + cache key)
│   └── seed/demo_leads.csv 50 B2B SaaS companies for zero-setup demo
└── tests/                  28 unit tests covering scorer, enricher, dedupe, csv_mapper, fallback

frontend/
└── src/
    ├── App.tsx                    single-page shell
    ├── api.ts                     thin fetch wrappers
    ├── types.ts
    └── components/
        ├── ICPForm.tsx            three-field ICP definition
        ├── UploadPanel.tsx        CSV drop, demo seed, reset
        ├── LeadTable.tsx          sortable, filterable, tier-badged table
        ├── LeadDrawer.tsx         signal breakdown bars + email generator
        └── TierBadge.tsx          A / B / C pill
```

### Gemini integration

Three places use Gemini when `GEMINI_API_KEY` is set, and **all three fall back gracefully** to the rule-based version when it's not:

| Feature | File | Without key | With key |
|---|---|---|---|
| **CSV column mapping** | `services/csv_mapper.py` | Alias dictionary covers Salesforce / HubSpot / Apollo / ZoomInfo headers | Adds Gemini fallback for unrecognized headers (e.g. `nom_entreprise`, custom CRM exports) |
| **Lead scoring** | `services/scorer_llm.py` | Substring keyword match | Semantic match — understands `"software-as-a-service"` = `"saas"` |
| **Email generation** | `services/outreach_llm.py` | 3-line template grounded in scraped facts | Genuinely varied 3-line emails written from the same facts |

**Why parallel files instead of editing the originals:** the rule-based code stays a known-good fallback that's independently tested. A future swap to OpenAI/Claude changes one file (`gemini.py`), not five. Every Gemini-powered function has the *same return shape* as its rule-based twin, so the UI and DB schema don't change.

**Throttling** (`services/gemini.py`): a sliding-window rate limiter caps the app at 12 RPM (under the free-tier 15 RPM ceiling). Scoring 50 leads at once is automatically paced — the first batch fires immediately, later calls wait their turn. No rate-limit errors reach the user.

**Failure handling**: the `gemini.py` wrapper catches every SDK exception and returns `None`. Every caller checks for `None` and falls back to its rule-based twin. Even with `GEMINI_API_KEY=invalid_key` the app is fully functional.

**Circuit breaker**: after 3 consecutive Gemini failures (expired key, exhausted quota, network outage), the wrapper opens a circuit and stops calling Gemini for the rest of the process — so a 50-lead scoring run doesn't pay the rate-limiter wait time on every single call. The header pill switches from green ("AI: Gemini") to red ("AI: rule-based (Gemini unavailable)") so the user understands what happened. Restart the backend to reset the breaker.

### Data model

| Table | Purpose |
|---|---|
| `icp` | singleton row holding the user's ICP |
| `leads` | one row per company; `domain` (normalized) is unique |
| `enrichment` | per-lead scrape result: title, description, tech stack, contacts, signals |
| `scores` | per-lead score, tier, reasons array, one-sentence "why" |
| `scrape_cache` | per-domain HTML cache, 7-day TTL — makes re-scoring with a tweaked ICP essentially free |

### The scoring brain (`backend/app/services/scorer.py`)

Weights sum to 100 and live in one constant — easy to tune. Each lead returns:
- `score` 0–100
- `tier` A (≥75), B (50–74), C (<50)
- `reasons[]` — full breakdown with raw value, weight, contribution, and contributing details
- `why` — single human sentence assembled from the top-contributing signals

The signal weights:

| Signal | Weight | Source |
|---|---|---|
| industry_match | 30 | ICP keywords ∩ (company name + industry + scraped page text) |
| size_band | 20 | employee count vs. ICP min/max, with soft fall-off outside the band |
| tech_relevance | 20 | growth-stack tech detected on site (HubSpot, Salesforce, Marketo, Intercom, Drift, Segment, Mixpanel, Amplitude, Pardot) |
| contact_completeness | 15 | email + phone + LinkedIn presence |
| activity_recency | 15 | hiring page + founded year (younger = higher) |

A lead with no scrapable site still scores on its CSV metadata — never silently zero.

## API

| Endpoint | Purpose |
|---|---|
| `GET /health` | liveness |
| `GET /system/status` | `{gemini_enabled, model}` — drives the AI-mode pill in the header |
| `GET /icp` / `PUT /icp` | read / update ICP singleton |
| `GET /leads` | list with score, tier, why, full enrichment |
| `GET /leads/{id}` | single lead |
| `POST /leads/upload` | multipart CSV upload (requires `company_name` column) |
| `POST /leads/seed` | load the 50-row demo set |
| `DELETE /leads` | clear everything |
| `GET /leads/export/csv?tier=A` | download HubSpot-shaped CSV |
| `POST /score` | enrich + score the full pipeline (parallel, cached) |
| `POST /outreach/{id}` | generate personalized 3-line cold email |

## What was deliberately *not* built

Bounded by the 5-hour budget, the following were explicitly out of scope:
- LLM-backed scoring/email generation — the `services/` boundary is shaped so a swap is one file
- User accounts / multi-tenant — single-user local tool
- Production deploy config — runs locally; Vercel/Render/Fly would each be ~30 min
- E2E browser tests — unit-tested the scoring brain instead, which is where the value lives

## Verification (also the demo script)

1. Start backend and frontend (above).
2. Open <http://127.0.0.1:5173>. Click **Load 50-lead demo set** — 50 unscored leads appear.
3. Edit ICP if you want; defaults are `saas, software, b2b` / 10–500 employees / generic value prop.
4. Click **Score all leads**. ~30s cold, <2s warm thanks to the scrape cache.
5. Sort by score ↓. Top leads are mid-market SaaS in the keyword set, running growth stacks. (In our reference run: Help Scout 85.7, LaunchDarkly 85.7, Hotjar 82.0, Retool 80.7. Salesforce, Snowflake, Databricks correctly slide to C tier — they're far outside the size band.)
6. Click any A-tier lead → drawer shows per-signal contribution bars and the contact info.
7. Click **Generate personalized email** → grounded in actual scraped facts, not a template.
8. Header → **Export CSV** → opens cleanly in Excel/HubSpot.

Run `pytest -q` from `backend/` for the 16 unit tests covering the scorer's weight math, tier thresholds, dedupe, and enricher signal extraction.

## Ethical scraping note

This tool only fetches public homepages of domains the user explicitly provided, at most 5 concurrent and 1 request/second per domain, with a 7-day cache to avoid re-hitting. The custom `LeadQualifier/0.1` User-Agent is honest about what we are. No paid enrichment APIs are required; no email harvesting beyond what companies publish on their own sites.
