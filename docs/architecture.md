# RiskPulse AI architecture

Milestone 1 uses a single Python backend module boundary with FastAPI, SQLAlchemy, and Alembic, plus a Next.js and TypeScript frontend. PostgreSQL runs locally through Docker Compose. Ingestion, NLP, and stress-testing modules remain inside the backend so the project can evolve without introducing microservices prematurely.

The current runtime paths are:

`Next.js status page -> GET /health -> SQLAlchemy connection -> PostgreSQL`

`Manual ingestion trigger -> source adapter (RSS or Reddit API) -> normalization/UTC/hash -> idempotent Article insert -> IngestionRun status`

`NLP processing trigger -> Article preprocessing -> alias entity extraction -> sentiment backend -> event rules -> deterministic impact score -> RiskSignal`

The migrations create persistence boundaries for articles, entities, risk signals, portfolio positions, scenarios, stress-test runs/results, and ingestion observability. Milestone 2 adds provider adapters, bounded retries, source isolation, deterministic demo loading, and article/ingestion endpoints. Milestone 3 adds retryable NLP processing states, signal metadata, and bounded signal APIs without portfolio relevance or stress-testing behavior.
