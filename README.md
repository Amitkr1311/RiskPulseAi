# RiskPulse AI

RiskPulse AI is an AI-powered financial risk intelligence and synthetic portfolio stress-testing prototype. The repository contains Milestones 1–3: project foundation, data ingestion, and the traceable article-to-risk-signal NLP pipeline.

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

Open <http://localhost:3000> for the status/NLP view and <http://localhost:8000/docs> for the API documentation.

## Ingestion and NLP demo

Live ingestion remains opt-in. Configure `NEWS_RSS_URL` and/or the Reddit OAuth variables only for sources you are allowed to access. `INGESTION_API_KEY` is optional for local/demo triggering; it is not production authentication.

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
- `GET /signals`, `GET /signals/{signal_id}`

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

Milestone 3 does not include a portfolio-aware score, ingestion scheduler, multilingual analysis, production entity master, trained event classifier, stress-testing calculations, or the complete dashboard. The recommended next step is Milestone 4 — Portfolio Stress Testing.
