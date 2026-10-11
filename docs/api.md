# RiskPulse AI ingestion API

This document covers the ingestion, NLP, portfolio, and Milestone 6 stress-testing endpoints.

## `GET /articles`

Query parameters:

- `limit`: 1–100, default 20.
- `offset`: 0–100000, default 0.
- `source`: optional provider source such as `news` or `reddit`.
- `processing_status`: optional `pending`, `processing`, `processed`, or `failed` filter.
- `published_from`, `published_to`: optional ISO-8601 timestamps.
- `search`: optional case-insensitive title/text search.

The response contains `items`, `total`, `limit`, and `offset`.

## `GET /articles/{article_id}`

Returns a normalized article or HTTP 404. Article records include the demo/live flag and processing status.

## `POST /ingestion/run`

Request body:

```json
{"sources": ["news", "reddit"], "limit": 25}
```

Each selected source gets an isolated run. A missing provider configuration is reported as `disabled`; authentication, rate-limit, timeout, malformed-response, validation, and database failures are summarized without exposing credentials or authorization headers.

## `POST /ingestion/demo`

Loads the deterministic `backend/data/demo_articles.json` fixture. Repeating the request skips records already present.

## `GET /ingestion/status`

Returns whether each live adapter is configured and the latest 20 ingestion runs with fetched, inserted, duplicate, failed, and sanitized error-category fields.

If `INGESTION_API_KEY` is configured, add `X-Ingestion-Key` to both POST requests. This is a lightweight local/demo control, not a substitute for production authentication.

## Milestone 3 NLP and signals

- `GET /nlp/status`: configured sentiment backend, model availability, article processing counts, and signal count.
- `POST /nlp/process-pending`: process a bounded batch. Body is optional; use `{"limit":25}` with a maximum of 100.
- `POST /nlp/process/{article_id}`: process one article and return `processed`, `skipped`, or `failed`.
- `GET /signals`: paginated persisted signals. Filters include detailed `event_type`, broad `event_group`, `source`, `entity`, `impact_min`, `impact_max`, `created_from`, and `created_to`.
- `GET /signals/taxonomy`: returns supported event groups, event types, and entity types for filter clients.
- `GET /signals/{signal_id}`: one signal with article source, entity mentions, sentiment probabilities, event confidence, impact factor breakdown, rationale, and model metadata.

NLP processing endpoints are bounded local/demo controls, not production authentication or rate limiting. The default backend is deterministic `heuristic`; optional FinBERT setup and its licensing limitation are documented in [`docs/nlp.md`](nlp.md).

## Milestone 4 API layer

- `GET /signals/latest?limit=10`: newest persisted signals, bounded to 50, using the standard `{items, total, limit, offset}` envelope.
- `GET /dashboard/summary`: calculated article, processing, signal, impact, recent-count, demo/live, and timestamp metrics.

Signal filters include `sentiment_label`, `sentiment_min`, `sentiment_max`, `is_demo`, and publication dates in addition to the Milestone 3 filters. All collection endpoints, including `/signals/latest`, return `items`, `total`, `limit`, and `offset`.

Signal detail includes both the flattened signal fields and an `article` object containing the original source article and processing metadata. Date ranges are validated with HTTP 422 for inverted bounds; missing records return HTTP 404; database failures return a sanitized HTTP 503 response.

Example frontend request:

```ts
const response = await fetch(`${apiUrl}/signals?limit=20&impact_min=7&is_demo=false`);
const page = await response.json(); // { items, total, limit, offset }
```

## Milestone 5 portfolio foundation

- `GET /portfolio`: demo portfolio metadata, position count, and exact Decimal totals in INR and crore.
- `GET /portfolio/positions`: paginated positions. Optional `asset_class` and `sector` filters are validated against the supported asset classes.
- `GET /portfolio/positions/{position_id}`: one position, its market value, contribution, sector, and validated asset-specific parameters.
- `GET /portfolio/summary`: base valuation totals, asset-class allocation, sector allocation, and position contribution. No stress calculation is performed.

Example requests:

```powershell
Invoke-RestMethod http://localhost:8000/portfolio
Invoke-RestMethod 'http://localhost:8000/portfolio/positions?asset_class=equity'
Invoke-RestMethod http://localhost:8000/portfolio/summary
```

Portfolio money fields are explicit: `market_value_inr` is canonical and `market_value_crore` is derived using `₹1 crore = ₹10,000,000`. See [`portfolio.md`](portfolio.md) for the deterministic seed and parameter units, and [`stress_testing.md`](stress_testing.md) for stress formulas and audit behavior.

## Live RSS and Reddit integration

## Social CSV replay

The `social` adapter replays a downloaded Kaggle tweets-vs-stock CSV through the same normalization, content-hash deduplication, and article persistence flow as RSS. Put the CSV at `backend/data/tweets-vs-stock.csv`, or set `SOCIAL_CSV_PATH` to another path. The adapter accepts common `Tweet`/`Text` content columns and optional ID, date, URL, and title columns; it does not create records when the file is absent. `/ingestion/status` always reports `news`, `social`, and optional `reddit` separately.

The repository does not include the Kaggle dataset. Download the permitted tweets-vs-stock CSV yourself and place the export at that exact path before running `POST /ingestion/run` with `{"sources":["social"],"limit":25}`.

Live polling is optional and disabled by default. Reddit ingestion is separately opt-in. Configure the provider credentials in the backend/root `.env` file, then enable the in-process poller:

```env
NEWS_RSS_URL=https://your-permitted-provider.example/feed.xml
REDDIT_INGESTION_ENABLED=false
REDDIT_ACCESS_TOKEN=your_oauth_access_token
REDDIT_SUBREDDITS=["finance","investing"]
REDDIT_SEARCH_TERMS=["banking","credit risk","interest rates"]
INGESTION_LIVE_ENABLED=true
INGESTION_LIVE_SOURCES=["news","reddit"]
INGESTION_LIVE_PROCESS_NLP=true
INGESTION_POLL_INTERVAL_SECONDS=300
```

Set `REDDIT_INGESTION_ENABLED=true` only when a valid Reddit OAuth access token is available; the token must be a raw bearer token, not a client ID or client secret. Restart the backend after changing environment variables. The scheduler polls configured sources, deduplicates and persists new articles, then processes pending articles through the configured NLP backend. The frontend reads `/ingestion/status`, `/articles`, `/nlp/status`, and `/signals` every 15 seconds; provider credentials never go to the browser.

For a multi-worker production deployment, run one dedicated scheduler/worker rather than enabling the in-process poller in every API worker, otherwise each worker may poll the providers.
