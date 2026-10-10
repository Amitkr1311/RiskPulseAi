# RiskPulse AI

RiskPulse AI is an AI-powered financial risk intelligence and synthetic portfolio stress-testing prototype. The repository now contains **Milestone 1 — Project Foundation** and **Milestone 2 — Data Ingestion**.

The project specification is [`docx/RiskPulse_AI_Project_Specification.md`](docx/RiskPulse_AI_Project_Specification.md). It is authoritative for architecture, scope, and milestone acceptance criteria.

## Prerequisites

- Node.js 20+
- Python 3.12+ (the current verification environment uses Python 3.14.2)
- Docker Desktop with Compose for PostgreSQL

## Local setup

1. Create local environment files from the placeholders:

   ```powershell
   Copy-Item .env.example .env
   Copy-Item frontend/.env.example frontend/.env.local
   ```

2. Start PostgreSQL:

   ```powershell
   docker compose up -d postgres
   docker compose ps
   ```

3. Set up the backend and install dependencies:

   ```powershell
   Set-Location backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. Apply migrations and load the foundation portfolio/scenario fixtures:

   ```powershell
   alembic upgrade head
   python -m app.db.seed
   ```

5. Start the API in one terminal:

   ```powershell
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. Install and start the frontend in another terminal:

   ```powershell
   Set-Location ../frontend
   npm install
   npm run dev
   ```

Open <http://localhost:3000> for the status page and <http://localhost:8000/docs> for the FastAPI documentation.

## Supported ingestion providers

Milestone 2 includes two independent, opt-in adapters:

- Financial news: configurable RSS/Atom feed through `NEWS_RSS_URL`. The adapter uses standard HTTP requests and does not assume the feed is free or licensed for redistribution; configure only a source permitted by its current terms.
- Social media: Reddit OAuth API through `REDDIT_ACCESS_TOKEN`, `REDDIT_API_BASE_URL`, `REDDIT_USER_AGENT`, `REDDIT_SUBREDDITS`, and optional `REDDIT_SEARCH_TERMS`. The adapter uses Reddit’s documented API and does not scrape pages.

Missing credentials or provider URLs disable the corresponding live adapter without preventing startup. API credentials are never written to logs or tracked files. Configure an optional `INGESTION_API_KEY` to require `X-Ingestion-Key` on ingestion-triggering endpoints; for local-only development it may remain blank.

`INGESTION_BATCH_SIZE`, `INGESTION_POLL_INTERVAL_SECONDS`, `INGESTION_REQUEST_TIMEOUT_SECONDS`, `INGESTION_MAX_RETRIES`, and `INGESTION_RETRY_BACKOFF_SECONDS` control bounded ingestion behavior. Milestone 2 exposes manual triggers; a scheduler is intentionally deferred.

## Ingestion API

- `GET /articles?limit=20&offset=0&source=news`: paginated stored articles. Optional `published_from` and `published_to` ISO-8601 filters are supported.
- `GET /articles/{article_id}`: one normalized article.
- `POST /ingestion/run`: fetch configured live sources. Example body: `{"sources":["news","reddit"],"limit":25}`.
- `POST /ingestion/demo`: load deterministic repository fixtures without credentials.
- `GET /ingestion/status`: recent runs, sanitized error categories, source configuration, and counts.

When `INGESTION_API_KEY` is set, send `X-Ingestion-Key` with the two POST requests. Provider failures are isolated per source and returned as run summaries rather than crashing the application.

## Demo mode

The deterministic fixtures are in [`backend/data/demo_articles.json`](backend/data/demo_articles.json). They include separate financial-news and Reddit-shaped records covering earnings, a credit event, a macroeconomic announcement, and a geopolitical event. Every fixture has `is_demo=true`; demo loading never labels records as live and is idempotent.

Load them either through the API:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/ingestion/demo
Invoke-RestMethod http://localhost:8000/ingestion/status
```

or from the backend command line:

```powershell
python -m app.ingestion.demo
```

Deduplication uses `(source, external_id)` when a provider ID exists. Records without a provider ID use `(source, content_hash)`, where the SHA-256 hash is based on normalized title and text. Database uniqueness constraints and savepoints protect against repeated or concurrent inserts.

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

External HTTP/API calls are mocked in tests. The tests do not require provider credentials or live provider availability.

## Scope boundaries

Included in Milestone 2: two provider adapters, common normalization, UTC timestamps, deduplication, bounded retries/timeouts, ingestion persistence, run statistics, source status, demo fixtures, and article/ingestion endpoints.

Not included: entity extraction, FinBERT/NLP, sentiment, event classification, impact scoring, stress-testing calculations, or the complete dashboard. Those belong to later milestones.

