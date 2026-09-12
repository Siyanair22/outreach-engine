# GTM Outreach Engine

A backend service that automates B2B prospect research and personalized cold-email
generation. Upload a list of companies, enrich them with public company data, and
generate outreach emails that reference specific details about each prospect.

Built with FastAPI, SQLAlchemy, and the Google Gemini API.

## How it works

Each prospect moves through a pipeline, tracked by a status field:

```
new → enriching → enriched → generating → email_generated → sent
                     ↓                          ↓
                   failed                     failed
```

1. **Upload** — add companies via CSV or one at a time through the API.
2. **Enrich** — fetch company description, industry, size, location, funding stage
   and contact details from Hunter.io.
3. **Generate** — feed the enriched profile to Gemini, which returns a subject line
   and body tailored to that company.

Emails can be regenerated with a different tone or extra context if the first
attempt misses.

## Requirements

- Python 3.10+ (the code uses `str | None` union syntax)
- API keys are **optional** — see [Running without API keys](#running-without-api-keys)

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Configure environment
cp backend/.env.example backend/.env
```

Then edit `backend/.env`:

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | No | Email generation. Free tier: 500 requests/day on Flash models. |
| `HUNTER_API_KEY` | No | Company and contact enrichment. Free tier: 25 searches/month. |
| `DATABASE_URL` | No | Defaults to `sqlite:///./gtm_outreach.db`. |

## Running

The app uses flat imports, so start it **from inside the `backend/` directory**:

```bash
cd backend
uvicorn main:app --reload
```

- API: <http://localhost:8000>
- Interactive docs (Swagger): <http://localhost:8000/docs>

The SQLite database and its tables are created automatically on first startup.

### Running without API keys

The service is designed to run end to end with no credentials configured. If a key
is missing, it falls back to built-in mock data — canned enrichment profiles for a
few well-known domains and a templated email. The full pipeline works, so you can
develop and demo against it before signing up for anything.

## Trying it out

`data/sample_prospects.csv` contains a handful of real companies in the expected
format. With the server running:

```bash
# Upload the sample prospects
curl -F "file=@data/sample_prospects.csv" http://localhost:8000/api/prospects/upload

# Enrich and generate an email for the first one
curl -X POST http://localhost:8000/api/prospects/1/enrich
curl -X POST http://localhost:8000/api/prospects/1/generate-email
```

### CSV format

Only `company_name` is required. Extra columns are ignored, and rows whose company
name already exists are skipped rather than duplicated.

```csv
company_name,domain,contact_name,contact_role,contact_email
Stripe,stripe.com,John Collison,Co-founder,
```

## API

### Prospects — `/api/prospects`

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Bulk-upload prospects from a CSV file |
| `POST` | `/` | Add a single prospect |
| `GET` | `/` | List prospects — supports `status`, `search`, `limit`, `offset` |
| `GET` | `/{id}` | Full prospect record, including any generated email |
| `POST` | `/{id}/enrich` | Fetch company and contact data |
| `POST` | `/{id}/generate-email` | Generate a personalized email |
| `POST` | `/{id}/regenerate-email` | Regenerate with new parameters, overwriting the previous email |
| `DELETE` | `/{id}` | Remove a prospect |

### Dashboard — `/api/dashboard`

| Method | Path | Description |
|---|---|---|
| `GET` | `/stats` | Total prospects, counts by status, and emails generated in the last 24h |

### Service

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Service name, version, status |
| `GET` | `/health` | Health check |

### Email generation parameters

Both generate endpoints accept an optional body:

| Field | Default | Description |
|---|---|---|
| `tone` | `professional` | `professional`, `casual`, or `direct` |
| `context` | — | Extra detail to work in, e.g. "They just raised a Series B" |
| `our_product` | CodeRound AI | What you're pitching |

The prompt constrains output to a subject under 60 characters, a body under 250
words, at least one company-specific detail, and a low-friction call to action.

## Project layout

```
backend/
├── main.py              # FastAPI app, CORS, startup
├── database.py          # SQLAlchemy models, session handling
├── schemas.py           # Pydantic request/response models
├── routers/
│   ├── prospects.py     # Prospect lifecycle endpoints
│   └── dashboard.py     # Pipeline metrics
└── services/
    ├── enrichment.py    # Hunter.io client + mock fallback
    └── llm_service.py   # Gemini client, prompt, mock fallback
data/
└── sample_prospects.csv # Test data
```

## Notes

- No frontend is included yet. CORS is pre-configured for local React dev servers
  on ports 3000 and 5173.
- The enrichment service is provider-agnostic by design — adding Clearbit, Apollo,
  or another source means implementing one function with the same return shape.
- `sent` exists as a pipeline status, but no email-sending integration is wired up.
