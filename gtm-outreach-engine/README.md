# GTM Outreach Engine

An AI-powered tool that automates prospect research and personalized outreach email generation for B2B sales teams.

**The problem:** Sales and GTM teams spend 30–45 minutes per prospect manually researching companies, finding the right contacts, and writing personalized outreach emails. This doesn't scale.

**The solution:** Upload a list of companies → the engine automatically enriches each prospect using external APIs → an LLM generates personalized outreach emails based on the enriched data → everything is tracked on a dashboard.

## Architecture

```
[CSV Upload / Manual Entry]
        ↓
[FastAPI Backend]
        ↓
[Enrichment Layer]──→ External APIs (company data, contacts)
        ↓
[LLM Layer]──→ Claude / OpenAI API (personalized email generation)
        ↓
[SQLite Database]──→ Stores prospects, enrichment data, generated emails
        ↓
[React Dashboard]──→ Pipeline view, email preview, campaign metrics
```

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **Frontend:** React, Tailwind CSS
- **AI/LLM:** Anthropic Claude API (for email personalization)
- **APIs:** Hunter.io (email finding), Clearbit (company enrichment)
- **Deployment:** Render (backend), Vercel (frontend)

## Features

- **CSV Upload:** Bulk-import prospect lists (company name, domain, role)
- **Auto-Enrichment:** Fetches company data, employee info, and contact details via APIs
- **LLM Email Generation:** Generates personalized outreach emails using Claude, tailored to each prospect's company and role
- **Pipeline Dashboard:** Track prospect status (new → enriched → email generated → sent)
- **Email Preview & Edit:** Review and edit generated emails before sending
- **Campaign Metrics:** Track emails generated, response rates, and pipeline health
- **Regenerate:** One-click email regeneration with different tones or angles

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- API keys: Anthropic (Claude), Hunter.io (optional), Clearbit (optional)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # Add your API keys
uvicorn main:app --reload
```

The API docs are auto-generated at `http://localhost:8000/docs` (Swagger UI).

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

Opens at `http://localhost:3000`.

### Sample Data
A sample CSV is included at `data/sample_prospects.csv` for testing.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/prospects/upload` | Upload CSV of prospects |
| POST | `/api/prospects` | Add a single prospect |
| GET | `/api/prospects` | List all prospects with status |
| GET | `/api/prospects/{id}` | Get prospect details + generated email |
| POST | `/api/prospects/{id}/enrich` | Trigger enrichment for a prospect |
| POST | `/api/prospects/{id}/generate-email` | Generate personalized outreach email |
| POST | `/api/prospects/{id}/regenerate-email` | Regenerate with different parameters |
| GET | `/api/dashboard/stats` | Pipeline metrics and campaign stats |

## Project Structure

```
gtm-outreach-engine/
├── README.md
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # SQLAlchemy models + DB setup
│   ├── schemas.py           # Pydantic request/response models
│   ├── routers/
│   │   ├── prospects.py     # Prospect CRUD + pipeline endpoints
│   │   └── dashboard.py     # Dashboard stats endpoint
│   ├── services/
│   │   ├── enrichment.py    # External API integrations
│   │   └── llm_service.py   # LLM email generation
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
├── frontend/
│   └── src/
├── data/
│   └── sample_prospects.csv
└── .gitignore
```

## Status

🚧 **Actively in development**

- [x] Backend API skeleton + database models
- [x] CSV upload and prospect management
- [x] LLM-powered email generation
- [ ] External API enrichment integration
- [ ] React dashboard
- [ ] Deployment

## Why I Built This

As someone with experience in both software engineering (JPMorgan Chase) and marketing/data analysis (FCB India, IIDE), I noticed that the outbound sales process is one of the most manual, repetitive workflows in B2B companies. This project applies engineering to a growth problem — automating the research-to-outreach pipeline that GTM teams run daily.

## License

MIT
