# Lead Qualifier

A sales-decision layer for messy lead lists. FastAPI backend + React frontend.
It imports CSV leads, enriches public websites, scores each lead against your ICP,
turns raw scores into action queues, and generates saved outreach drafts.

## Product Features

- Action Queue: Ready Now, Needs Research, Missing Contact, Low ICP Fit, and Unscored worklists.
- ICP scoring: editable scoring weights, templates, explainable signal breakdowns, and score history.
- Pipeline board: New, Contacted, Qualified, and Dead stages with persisted history.
- CSV preview: detected columns, editable mappings, invalid rows, duplicate counts, then confirm import.
- Lookalikes: find 20 similar leads from a strong account and export that segment to CSV.
- Outreach drafts: direct, warm, and executive tones; saved draft history; copy sequence and mark contacted.
- Export: HubSpot-shaped CSV with score, tier, confidence, risks, contact info, and rationale.

## Setup

Requires **Python 3.10+** and **Node 18+**.

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload     # http://127.0.0.1:8000
```

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev                       # http://127.0.0.1:5173
```

Open <http://127.0.0.1:5173>. Vite proxies `/api/*` to the backend.

### 3. Optional: Enable OpenAI

Without a key the app uses rule-based scoring and email templates. With a key,
three features upgrade: semantic lead scoring, personalized email generation,
and intelligent CSV column mapping.

1. Get a key at <https://platform.openai.com/api-keys>
2. Copy `backend/.env.example` to `backend/.env`
3. Set `OPENAI_API_KEY=your_key_here`
4. Restart the backend

The header pill switches from amber **AI: rule-based** to green **AI: OpenAI**
when the key is active.

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest -q
cd frontend && npx tsc -b
```

37 backend tests cover scoring, enrichment, dedupe, CSV mapping, workflow ranking,
pipeline stages, lookalikes, and OpenAI fallback.

## Dataset

A demo dataset of **50 B2B SaaS companies** ships at
[`backend/app/seed/demo_leads.csv`](backend/app/seed/demo_leads.csv). It contains
only public information: company name, website, industry, employee count, and
headquarters. Click **Load 50-lead demo set** in the UI to ingest it.

You can also upload your own CSV. The only required field after mapping is
`company_name`. Optional fields are `website`, `industry`, `employee_count`, and
`location`.

## Quick Demo

1. Click **Load 50-lead demo set**.
2. Click **Score all leads**.
3. Use the **Action Queue** to pick Ready Now or Needs Research leads.
4. Open a lead, review score history, generate outreach, and copy it as contacted.
5. Run **Find 20 more like this** from a strong lead and export the lookalike list.
