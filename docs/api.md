# RiskPulse AI ingestion API

Milestone 2 exposes only the ingestion and article endpoints needed to verify normalized persistence. It does not expose NLP signals or stress-testing endpoints yet.

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
- `GET /signals`: paginated persisted signals. Filters include `event_type`, `source`, `entity`, `impact_min`, `impact_max`, `created_from`, and `created_to`.
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
