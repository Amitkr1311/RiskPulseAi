# RiskPulse AI

RiskPulse AI is an AI-powered financial risk intelligence and synthetic portfolio stress-testing prototype. The repository contains the project foundation, two-source data ingestion, the traceable article-to-risk-signal NLP pipeline, API integration, synthetic portfolio construction, and deterministic stress testing.

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

If `INGESTION_API_KEY` is set in the backend/root `.env`, the local Next.js replay proxy reads it server-side. In another environment, set the same server-only variable in the frontend runtime as `INGESTION_API_KEY=...` (without the `NEXT_PUBLIC_` prefix). The key is never sent to the browser. Leave it blank for an unprotected local demo.

## Local datasets and import commands

The local transaction export is `data/transactions.csv` (806 rows with `Date`, `Description`, `Amount`, `Transaction Type`, `Category`, and `Account Name`). The local historical social export is `backend/data/tweets-vs-stock.csv` (80,793 rows with `Date`, `Tweet`, `Stock Name`, and `Company Name`). These files are user-supplied downloads and are not redistributed by the project. No license or attribution metadata is included beside the CSVs in this repository; retain the original provider attribution and verify its terms before sharing them.

Build the database-backed synthetic portfolio from the transaction categories:

```powershell
python scripts/build_portfolio.py --input data/transactions.csv
Set-Location backend
alembic upgrade head
python -m app.db.seed
```

The builder validates dates and amounts, removes exact duplicate rows, uses debit transactions to derive recurring and sector proxies, and writes clearly labelled synthetic positions to `backend/data/portfolio_seed.json`. The demo seed preserves the specification's ₹100 crore total, keeps derivative notional separate from marked-to-market value, and includes named Tesla, Apple, Microsoft, and HDFC Bank loan, bond, and equity exposures for signal-to-portfolio demonstrations. Consumer transactions are not treated as proof of actual loans, bonds, equities, or derivatives.

Replay the historical social file through the shared article and NLP pipeline:

```powershell
Set-Location backend
Invoke-RestMethod -Method Post -Uri http://localhost:8000/ingestion/run -ContentType application/json -Body '{"sources":["social"],"limit":25}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/nlp/process-pending -ContentType application/json -Body '{"limit":25}'
```

The ingestion endpoint is bounded to 100 records per request. For the full replay, repeat the social request with `offset` values `0`, `100`, `200`, and so on; the adapter reads deterministic CSV slices and the shared flow deduplicates safely.

Social records are stored as `source="social"`, marked as historical replay data, and retain the CSV timestamp, tweet text, stock symbol, and company attribution. They are not a live social feed and the CSV does not supply stock-return labels used by the risk engine. Repeat ingestion is deduplicated by source identifier when available or normalized content hash.

### Historical social replay controls

The News page includes a bounded replay worker for the same CSV. It processes one small batch at a time through the social adapter, article deduplication, NLP scoring, risk-signal persistence, and the existing automatic stress-test trigger. Replay state and the cursor are stored in PostgreSQL, so a backend restart preserves progress and marks an interrupted worker as stopped. Reset moves the cursor to the beginning without deleting articles or signals.

The controls call these endpoints:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/replay/start -ContentType application/json -Body '{"speed_records_per_second":1,"batch_size":1}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/replay/pause
Invoke-RestMethod -Method Post -Uri http://localhost:8000/replay/resume
Invoke-RestMethod -Method Post -Uri http://localhost:8000/replay/stop
Invoke-RestMethod -Method Post -Uri http://localhost:8000/replay/reset
Invoke-RestMethod http://localhost:8000/replay/status
```

Supported UI speeds are 1, 5, and 10 records per second; the backend enforces a maximum configured by `REPLAY_MAX_SPEED` (10 by default). `start` resumes a stopped/error replay from its saved position. Starting a completed replay begins a new pass but keeps previously persisted data, so those rows are counted as duplicates. `resume` is only for a paused replay, and `reset` is rejected while a worker is active. The frontend uses two-second bounded polling for status and refreshes the news feed as the cursor advances; no fake live indicator is shown.

Replayed articles retain the original historical `published_at` timestamp and a separate database `ingested_at` timestamp. If the CSV is missing, empty, malformed, or NLP fails, the status panel reports the error and the saved cursor remains available for retry. Historical replay cannot reproduce a live social API's delivery order, deleted posts, engagement data, or market-return labels.

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

The demo fixture includes two named-company articles. After the NLP command, their impact scores exceed 7 and automatically create targeted credit or regulatory stress runs. Open the Stress Testing page and inspect the newest automatic run to see the triggering article and the matched named positions.

The same processing is available from the backend with `python -m app.nlp.process --limit 25`. See [`docs/nlp.md`](docs/nlp.md) for the pipeline, FinBERT setup, scoring formula, taxonomy, and limitations.

For the optional FinBERT demo, install `backend/requirements-finbert.txt`, then set `NLP_SENTIMENT_BACKEND=finbert` and `NLP_ALLOW_MODEL_DOWNLOAD=true` before processing. Tests and normal demo runs keep the safe heuristic default. The supplied three-row PhraseBank smoke fixture scores accuracy `1.0000` and macro-F1 `1.0000`; these numbers are not full-dataset benchmark results. See [`docs/research.md`](docs/research.md) for the full evaluation command.

## API surface

- `GET /health`
- `GET /articles`, `GET /articles/{article_id}`
- `POST /ingestion/run`, `POST /ingestion/demo`, `GET /ingestion/status`
- `GET /replay/status`, `POST /replay/start`, `POST /replay/pause`, `POST /replay/resume`, `POST /replay/stop`, `POST /replay/reset`
- `GET /nlp/status`, `POST /nlp/process-pending`, `POST /nlp/process/{article_id}`
- `GET /signals`, `GET /signals/latest`, `GET /signals/{signal_id}`
- `GET /signals/taxonomy`
- `GET /dashboard/summary`
- `GET /portfolio`, `GET /portfolio/positions`, `GET /portfolio/positions/{position_id}`, `GET /portfolio/summary`
- `GET /stress-testing/scenarios`, `POST /stress-testing/run`, `GET /stress-testing/runs`, `GET /stress-testing/runs/{simulation_id}`
- `GET /research/sentiment-evaluation`, `GET /research/market-data`, `GET /research/event-window`

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

Optional Financial PhraseBank evaluation and yfinance historical market research are documented in [`docs/research.md`](docs/research.md). These workflows require explicit commands and network access when downloading external data; normal application startup and demo mode do not.

## Scope boundaries

The current implementation includes the database-backed portfolio, deterministic scenario execution, signal eligibility and relevance, persisted audit snapshots, idempotent runs, position-level reconciliation, automatic qualifying signal triggers, and the before/after stress-testing dashboard.
