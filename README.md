# Lead Qualifier

A lead-scoring tool built for Caprae Capital's AI-Readiness Pre-Screening Challenge.
FastAPI backend + React frontend. Scores a CSV of company leads against your ICP and generates a personalized cold email per lead.

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

### 3. (Optional) Enable Gemini AI

Without a key the app uses rule-based scoring + email templates. With a key, three features upgrade: semantic lead scoring, personalized email generation, and intelligent CSV column mapping.

1. Get a free key at <https://aistudio.google.com/apikey>
2. Copy `backend/.env.example` to `backend/.env`
3. Set `GEMINI_API_KEY=your_key_here`
4. Restart the backend

The header pill switches from amber **AI: rule-based** to green **AI: Gemini** when the key is active.

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest -q
```

28 unit tests covering the scorer, enricher, dedupe, CSV mapper, and Gemini fallback.

## Dataset

A demo dataset of **50 B2B SaaS companies** ships at [`backend/app/seed/demo_leads.csv`](backend/app/seed/demo_leads.csv). It contains only public information (company name, website, industry, employee count, headquarters) for well-known SaaS companies — Notion, Linear, Vercel, Figma, Slack, etc. Click **Load 50-lead demo set** in the UI to ingest it; no setup required.

You can also upload your own CSV. The only required column is `company_name`. Optional columns: `website`, `industry`, `employee_count`, `location`. Common header variations (`Company`, `Account Name`, `URL`, `Headcount`, etc.) are auto-mapped. With Gemini enabled, even non-English headers (e.g. `nom_entreprise`) get mapped automatically.

## Quick demo

1. Click **Load 50-lead demo set**
2. Click **Score all leads** (~30s cold, <2s warm — scrape results cached 7 days)
3. Sort by score, click any A-tier lead, click **Generate personalized email**
4. Click **Export CSV** in the header to download a HubSpot-shaped file
