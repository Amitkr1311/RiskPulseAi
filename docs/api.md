# RiskPulse AI ingestion API

Milestone 2 exposes only the ingestion and article endpoints needed to verify normalized persistence. It does not expose NLP signals or stress-testing endpoints yet.

## `GET /articles`

Query parameters:

- `limit`: 1–100, default 20.
- `offset`: 0–100000, default 0.
- `source`: optional provider source such as `news` or `reddit`.
- `published_from`, `published_to`: optional ISO-8601 timestamps.

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
