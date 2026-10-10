# RiskPulse AI

RiskPulse AI is an AI-powered financial risk intelligence and synthetic portfolio stress-testing prototype. The repository contains Milestones 1–5: project foundation, data ingestion, the traceable article-to-risk-signal NLP pipeline, API integration, and the synthetic portfolio foundation.

The project specification is [`docx/RiskPulse_AI_Project_Specification.md`](docx/RiskPulse_AI_Project_Specification.md) and is authoritative for architecture, scope, and milestone acceptance criteria.

## Prerequisites

- Node.js 20+
- Python 3.12+ (the current verification environment uses Python 3.14.2)
- Docker Desktop with Compose for PostgreSQL

## Local setup

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
docker compose up -d postgres

Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

To enable optional live RSS/Reddit polling, set `NEWS_RSS_URL` and the `INGESTION_LIVE_*` variables in `.env`. Reddit additionally requires `REDDIT_INGESTION_ENABLED=true` and a valid OAuth access token. Restart the backend after changing environment variables. The frontend automatically refreshes live-feed status, recent articles, NLP status, and signals every 15 seconds. Provider credentials remain backend-only. See [`docs/api.md`](docs/api.md#live-rss-and-reddit-integration).

Open <http://localhost:3000> for the status/NLP view and <http://localhost:8000/docs> for the API documentation.

## Ingestion and NLP demo

Live ingestion remains opt-in. Configure `NEWS_RSS_URL` and/or the Reddit OAuth variables only for sources you are allowed to access. Reddit is disabled unless `REDDIT_INGESTION_ENABLED=true`. `INGESTION_API_KEY` is optional for local/demo triggering; it is not production authentication.

Load deterministic demo articles and process them:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/ingestion/demo
Invoke-RestMethod -Method Post -Uri http://localhost:8000/nlp/process-pending -ContentType application/json -Body '{"limit":25}'
Invoke-RestMethod http://localhost:8000/signals
```

The same processing is available from the backend with `python -m app.nlp.process --limit 25`. See [`docs/nlp.md`](docs/nlp.md) for the pipeline, FinBERT setup, scoring formula, taxonomy, and limitations.

## API surface

- `GET /health`
- `GET /articles`, `GET /articles/{article_id}`
- `POST /ingestion/run`, `POST /ingestion/demo`, `GET /ingestion/status`
- `GET /nlp/status`, `POST /nlp/process-pending`, `POST /nlp/process/{article_id}`
- `GET /signals`, `GET /signals/latest`, `GET /signals/{signal_id}`
- `GET /dashboard/summary`
- `GET /portfolio`, `GET /portfolio/positions`, `GET /portfolio/positions/{position_id}`, `GET /portfolio/summary`
- `GET /stress-testing/scenarios`, `POST /stress-testing/run`, `GET /stress-testing/runs`, `GET /stress-testing/runs/{simulation_id}`

Collection responses use `{items, total, limit, offset}`. Articles support `source`, `processing_status`, `published_from`, `published_to`, and `search`. Signals support entity, event, sentiment, impact, source, demo/live, publication, and signal-creation filters. Signal details include the original nested article. Portfolio responses use exact INR values plus derived crore values and provide base valuation only. See [`docs/api.md`](docs/api.md) and [`docs/portfolio.md`](docs/portfolio.md) for request examples, formulas, and validation behavior.

## Verification commands

Backend:

```powershell
Set-Location backend
pytest
python -m compileall -q app migrations tests
alembic upgrade head
```

Frontend:

```powershell
Set-Location frontend
npm run lint
npm run typecheck
npm run build
```

Tests use deterministic fixtures and mocked provider/model boundaries; they do not require live provider credentials or a model download. FinBERT is optional and its model page does not declare a license, so commercial use requires legal review.

## Scope boundaries

Milestone 5 adds the synthetic portfolio foundation, deterministic seed, base valuation endpoints, and scenario templates. It does not include stress-testing calculations, event triggers, signal mapping, or the complete dashboard.

Milestone 6 adds deterministic scenario execution, signal eligibility, portfolio relevance, persisted audit snapshots, idempotent runs, and position-level reconciliation. Automatic ingestion-to-stress background triggering and the complete dashboard remain later integration scope.
