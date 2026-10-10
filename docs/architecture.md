# RiskPulse AI architecture

Milestone 1 uses a single Python backend module boundary with FastAPI, SQLAlchemy, and Alembic, plus a Next.js and TypeScript frontend. PostgreSQL runs locally through Docker Compose. Ingestion, NLP, and stress-testing modules are reserved inside the backend so the project can evolve without introducing microservices prematurely.

The current runtime path is:

`Next.js status page → GET /health → SQLAlchemy connection → PostgreSQL`

The foundation migration creates the persistence boundaries for articles, entities, risk signals, portfolio positions, scenarios, stress-test runs/results, and ingestion observability. Calculations and provider integrations are intentionally deferred to their specified milestones.

