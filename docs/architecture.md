# RiskPulse AI architecture

Milestone 1 uses a single Python backend module boundary with FastAPI, SQLAlchemy, and Alembic, plus a Next.js and TypeScript frontend. PostgreSQL runs locally through Docker Compose. Ingestion, NLP, and stress-testing modules are reserved inside the backend so the project can evolve without introducing microservices prematurely.

The current runtime paths are:

`Next.js status page → GET /health → SQLAlchemy connection → PostgreSQL`

`Manual ingestion trigger → source adapter (RSS or Reddit API) → normalization/UTC/hash → idempotent Article insert → IngestionRun status`

The foundation migrations create the persistence boundaries for articles, entities, risk signals, portfolio positions, scenarios, stress-test runs/results, and ingestion observability. Milestone 2 adds the RSS and Reddit adapter boundaries, bounded retries, source isolation, deterministic demo loading, and article/ingestion endpoints. Calculations and NLP processing remain intentionally deferred to their specified milestones.
