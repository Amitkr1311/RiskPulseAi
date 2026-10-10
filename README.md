# RiskPulse AI

RiskPulse AI is an AI-powered financial risk intelligence and synthetic portfolio stress-testing prototype. This repository currently contains **Milestone 1 — Project Foundation** only.

The project specification is [`docx/RiskPulse_AI_Project_Specification.md`](docx/RiskPulse_AI_Project_Specification.md). The source specification is authoritative for architecture, scope, and acceptance criteria.

## Prerequisites

- Node.js 20+
- Python 3.12+
- Docker Desktop with Compose

## Local setup

1. Create a local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start PostgreSQL:

   ```powershell
   docker compose up -d postgres
   docker compose ps
   ```

3. Set up the backend virtual environment and install dependencies:

   ```powershell
   py -3.12 -m venv backend/.venv
   .\backend\.venv\Scripts\Activate.ps1
   python -m pip install -r backend/requirements.txt
   ```

4. Apply migrations and load deterministic foundation fixtures:

   ```powershell
   Set-Location backend
   alembic upgrade head
   python -m app.db.seed
   Set-Location ..
   ```

5. Start the API in one terminal:

   ```powershell
   Set-Location backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. Install and start the frontend in another terminal:

   ```powershell
   Set-Location frontend
   npm install
   npm run dev
   ```

Open <http://localhost:3000> for the status page and <http://localhost:8000/docs> for the FastAPI documentation.

## Verification commands

Backend:

```powershell
Set-Location backend
pytest
alembic upgrade head
```

Frontend:

```powershell
Set-Location frontend
npm run lint
npm run typecheck
npm run build
```

The backend tests use an isolated in-memory SQLite database. Local development and migrations use PostgreSQL through Docker Compose.

## Milestone 1 scope

Included: project configuration, PostgreSQL Compose service, SQLAlchemy models, Alembic migration, deterministic seed files, FastAPI health endpoint, frontend status page, and baseline checks.

Not included: live ingestion adapters, NLP/FinBERT processing, event classification, stress-testing calculations, or the complete dashboard. Those belong to later milestones.

