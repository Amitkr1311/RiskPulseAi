RISKPULSE AI  |  PROJECT SPECIFICATION 

# **RiskPulse AI** 

## **AI-Powered Financial Risk Intelligence & Portfolio Stress Testing** 

Codex Build Specification 

Module B — Strategic Portfolio Stress Testing 

Version 1.0 | October 2026 

Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

## **1. Executive Summary** 

RiskPulse AI is a hackathon-ready financial risk intelligence platform. It ingests financial news and social-media text, identifies companies and events, generates structured NLP risk signals, and uses qualifying events to trigger stress tests against a synthetic banking portfolio. The dashboard explains the detected event, the scenario assumptions, and the resulting hypothetical portfolio impact. 

The project is a simulation and decision-support prototype, not a trading system. It must not present hypothetical losses as actual market forecasts or financial advice. 

## **2. Problem Statement** 

Financial institutions receive large volumes of unstructured information from news outlets and social platforms. Important events can affect borrowers, securities, interest rates, credit spreads, commodities, and other portfolio exposures. RiskPulse AI automates the first stage of risk monitoring by turning text into structured signals and then demonstrating how a defined event could affect a synthetic portfolio under explicit scenario assumptions. 

### **2.1 Core flow** 

1. Ingest text from at least two independent sources. 

2. Normalize and deduplicate articles and posts. 

3. Extract companies/entities and analyze financial sentiment. 

4. Classify the event and estimate an impact score. 

5. Expose the resulting signal through a documented API. 

6. Map qualifying events to a predefined stress scenario. 

7. Revalue synthetic portfolio positions and calculate portfolio-level and asset-level impacts. 

8. Display the event, assumptions, calculations, and results in a dashboard. 

## **3. Scope and Non-Goals** 

### **3.1 In scope** 

- Two source adapters: one financial-news source and one social-media source. 

- Financial sentiment score from -1.0 to +1.0. 

- Event classification with a documented set of categories. 

- Impact score from 1 to 10, with transparent rationale. 

- Entity extraction and entity normalization where feasible. 

- PostgreSQL persistence and FastAPI endpoints. 

- Synthetic portfolio with a starting value of ₹100 crore. 

- Event-to-scenario mapping and deterministic stress calculations. 

- Responsive dashboard, event feed, portfolio view, and stress-test results. 

- Demo mode that works without external API credentials. 

- Automated tests, documentation, deployment configuration, and a five-minute demo. 

### **3.2 Out of scope for the first version** 

- Real-money trading or automatic trade execution. 

- Claims of reliably predicting future market prices. 

- Training a foundation model from scratch. 

- Complex production-grade derivatives pricing. 

- A distributed microservices architecture or mandatory Kafka cluster. 

- Paid services being required for the application to run in demo mode. 

Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

## **4. Recommended Technology Stack** 

|**Layer**|**Technology**|**Purpose**|
|---|---|---|
|**Frontend**|Next.js + TypeScript|Dashboard and user interactions|
|**Styling/UI**|Tailwind CSS + reusable<br>components|Responsive interface and design<br>consistency|
|**Charts**|Recharts|Portfolio values, asset losses, and<br>timelines|
|**Backend API**|Python + FastAPI|Risk signals, portfolio, scenarios,<br>and results|
|**Validation**|Pydantic|Typed API inputs and outputs|
|**Database access**|SQLAlchemy + Alembic|Persistence and schema migrations|
|**Database**|PostgreSQL|Articles, signals, portfolio,<br>scenarios, and results|
|**NLP**|Hugging Face Transformers +<br>FinBERT|Financial sentiment analysis|
|**Testing**|pytest + frontend lint/type checks|Automated quality checks|
|**Local environment**|Docker Compose|Repeatable development<br>environment|
|**Deployment**|Vercel + a Python-compatible host|Frontend and backend hosting|



Keep ingestion, NLP, API, and stress-testing code as modules inside the Python backend initially. Avoid splitting the system into microservices unless a measured need emerges. Verify current provider access, pricing, and model licensing before committing to an external service. 

## **5. High-Level Architecture** 

9. External sources: financial news API/RSS and a social-media API with legitimate access. 

10. Ingestion adapters: fetch records, normalize fields, retain source metadata, and handle provider failures. 

11. Processing: clean text, deduplicate records, normalize timestamps, and extract entities. 

12. NLP risk engine: sentiment analysis, event classification, and explainable impact scoring. 

13. Persistence/API: PostgreSQL stores raw records, risk signals, portfolio positions, scenario definitions, and simulation results; FastAPI exposes them. 

14. Stress-testing engine: checks trigger conditions, selects a scenario, applies asset-specific shocks, and calculates changes in valuation. 

15. Dashboard: displays source data, signals, portfolio exposure, scenario assumptions, and results. 

## **6. Data Contracts** 

### **6.1 Normalized article/post** 

{ 

"source": "news | reddit | other", 

"external_id": "provider-specific-id", 

- "title": "Source title", 

"text": "Normalized text content", 

- "url": "https://...", 

"published_at": "ISO-8601 timestamp or null", 

- "ingested_at": "ISO-8601 timestamp" 

} 

Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

### **6.2 Risk signal** 

{ 

"article_id": "database identifier", 

- "entity_name": "Company or entity", 

- "entity_id": "normalized identifier or null", 

"sentiment_score": -0.72, 

- "event_type": "company_performance", 

- "impact_score": 8, 

"confidence": 0.89, 

"explanation": "Short, evidence-linked rationale", 

"model_version": "configured model/version", 

"created_at": "ISO-8601 timestamp" 

} 

Example values are illustrative, not actual model outputs. Confidence must not be conflated with impact. Define how sentiment is derived from model probabilities and document the event taxonomy. An impact score is a heuristic estimate unless validated against a labeled dataset. 

## **7. Data Ingestion Requirements** 

- Implement separate adapter interfaces for each source. 

- Support configurable polling intervals and batch sizes. 

- Normalize source records to the common schema. 

- Deduplicate using provider IDs where available and stable content hashes otherwise. 

- Use timeouts, bounded retries, rate-limit handling, and structured error logs. 

- Do not scrape sites in ways that violate their terms or access restrictions. 

- Distinguish live records from seeded demo fixtures in storage and the UI. 

- Ensure a source outage does not break the rest of the application. 

- Provide a deterministic demo dataset and a manual demo-event action. 

## **8. NLP Risk Engine Requirements** 

### **8.1 Sentiment** 

Use a pretrained financial sentiment model such as FinBERT where practical. Return a score in [-1, 1], plus the predicted sentiment label and class probabilities when available. Document the score conversion and test it against representative examples. 

### **8.2 Event classification** 

Define a controlled taxonomy: geopolitical, macroeconomic, credit_event, merger_acquisition, earnings, regulatory, product_launch, market_crash, company_performance, and other. Use a suitable pretrained classifier or a transparent rules-plus-model approach. Return the category, confidence where available, and an explicit unknown/other result for uncertain inputs. 

### **8.3 Entity extraction** 

Extract organization/company mentions and normalize aliases when feasible. Do not assume the first company mentioned is always the affected entity. If entity resolution is uncertain, preserve the raw mention and mark it unresolved. 

Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

### **8.4 Impact scoring** 

Produce an integer score from 1 to 10 using a documented and testable method. A possible initial heuristic can combine event severity, sentiment magnitude, source reliability, and entity/portfolio relevance. Normalize inputs and define score bands. Do not imply that the score is a statistically calibrated market-impact probability. 

## **9. Synthetic Portfolio and Financial Model** 

|**Asset type**|**Initial value**|**Modeling notes**|
|---|---|---|
|**Corporate loans**|₹40 crore|Borrower/sector exposure; default<br>and recovery assumptions|
|**Government bonds**|₹25 crore|Duration or interest-rate sensitivity|
|**Corporate bonds**|₹20 crore|Duration and credit-spread|
|||sensitivity|
|**Equities**|₹10 crore|Market/sector return shock<br>i|
|**Derivatives**|₹5 crore|Clearly documented simplified<br>exposure and sensitivity|



**Initial portfolio total: ₹100 crore.** Seed values must reconcile exactly. Define whether each position is represented by market value, exposure, or notional; do not mix these concepts without explicit valuation rules. 

## **10. Stress Scenarios** 

|**Event category**|**Example shock**|**Required modeling care**|
|---|---|---|
|**Geopolitical**|Equity/commodity and relevant<br>credit shocks|Apply only to modeled exposures;<br>avoid blanket losses without<br>rationale|
|**Macroeconomic**|Interest-rate shift|Reprice bonds based on duration or<br>a documented approximation|
|**Credit event**|Default or credit-spread widening<br>i|Use borrower exposure,<br>probability/default assumptions,<br>and recovery rate<br>f|
|**Regulatory**|Sector-specific valuation shock|Map affected entities/sectors to<br>portfolio positions|
|**Market crash**|Broad equity decline and volatility<br>shock|Apply market shocks to appropriate<br>assets; document derivatives<br>simplification|



Example trigger: impact_score > 7 and an event type with a supported scenario, subject to portfolio relevance. Store a unique trigger key so reprocessing the same source event does not create duplicate runs. Allow manual scenario execution. Keep all scenario inputs deterministic for reproducible demos. 

### **10.1 Calculation outputs** 

- P&L = portfolio_value_after - portfolio_value_before 

- Loss percentage = (portfolio_value_before - portfolio_value_after) / portfolio_value_before × 100 

- Asset contribution = stressed asset value - initial asset value 

- Sum of asset-level contributions must equal the portfolio-level P&L within a documented rounding tolerance. 

## **11. API Design** 

|**Endpoint**|**Purpose**|
|---|---|
|**GET /health**|Service and dependency health<br>i|
|**GET /articles**|Paginated articles/posts; source and date filters|
|**GET /signals**|Paginated risk signals;entity,event,impact,and date|



Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

||filters|
|---|---|
|**GET /signals/latest**|Latest signals|
|**GET /signals/{signal_id}**|Signal detail with source article|
|**GET /portfolio**|Positions and initial valuation|
|**GET /scenarios**|Scenario definitions and assumptions|
|**POST /stress-tests/run**|Run a scenario or eligible event simulation|
|**GET /stress-tests**|Historical simulation runs|
|**GET /stress-tests/{run_id}**|Run detail and asset-level contribution|
|**GET /dashboard/summary**|Summarymetrics for dashboard cards|



## **12. Database Entities** 

- Article: source, external ID, title, text, URL, timestamps, content hash, demo/live flag, processing status. 

- Entity: canonical name, identifier/ticker where available, aliases, entity type. 

- ArticleEntity: article-to-entity relationship and extraction metadata. 

- RiskSignal: article reference, entity, sentiment, event type, impact, confidence, explanation, model version, timestamp. 

- PortfolioPosition: asset type, market value/exposure, currency, sector/borrower mapping, valuation parameters. 

- StressScenario: name, event category, threshold, shock parameters, version, and assumptions. 

- StressTestRun: trigger signal, scenario, before/after values, P&L, loss percentage, run status, timestamp. 

- StressTestResult: run, position, before/after position values, contribution, and calculation details. 

- IngestionRun or ProviderStatus: source status, counts, timestamps, and errors for observability. 

## **13. Dashboard Requirements** 

- Overview: portfolio value, latest high-impact events, recent stress runs, and aggregate simulated impact. 

- Event feed: source badge, title, time, entity, sentiment, event type, impact score, and source link. 

- Risk details: explanation, confidence, model metadata, and original article. 

- Portfolio: asset allocation and exposure table. 

- Stress testing: scenario selector, assumptions, trigger information, and manual run action. 

- Results: before/after value, P&L, loss percentage, asset contribution chart, and scenario assumptions. 

- Timeline: chronological events and associated stress-test runs. 

- Live/demo status: persistent indicator that distinguishes actual provider records from fixtures. 

## **14. Security, Reliability, and Quality** 

- Store credentials only in environment variables; never commit secrets. 

- Provide .env.example containing placeholder values only. 

- Validate all API input and output schemas. 

- Use database migrations; do not rely on manual schema edits. 

- Use bounded retries and timeouts for external services. 

- Make ingestion and event processing idempotent. 

- Log failures and trace an event from source article to signal and stress-test run. 

- Use deterministic fixtures and no random fake predictions in demo mode. 

- Avoid displaying untrusted article content as raw HTML. 

- Document model limitations and financial-model simplifications. 

- Do not treat sentiment alone as proof of a financial event or as an instruction to trade. 

Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

## **15. Repository Structure** 

riskpulse-ai/ frontend/ app/ components/ lib/ types/ backend/ app/ api/ core/ db/ models/ schemas/ services/ ingestion/ nlp/ stress_testing/ main.py migrations/ tests/ data/ demo_articles.json portfolio_seed.json scenarios.json docs/ PROJECT_SPEC.md architecture.md api.md demo-script.md docker-compose.yml .env.example .gitignore README.md 

## **16. Milestone-by-Milestone Build Plan** 

### **Milestone 1 — Foundation** 

Implementation: Inspect repository; initialize frontend/backend; add configuration, database, migrations, schemas, seed data, health checks, Docker Compose, and baseline tests. 

**Exit criteria:** Both services start; database initializes; health checks pass. 

Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

### **Milestone 2 — Ingestion** 

Implementation: Implement two independent adapters, common schema, normalization, deduplication, retry/timeouts, provider status, and demo fixtures. 

**Exit criteria:** Two sources can be represented in the normalized schema; provider failure does not break demo mode. 

### **Milestone 3 — NLP** 

Implementation: Implement entity extraction, FinBERT sentiment, event classification, impact score, explanations, model configuration, and unit tests. 

**Exit criteria:** A fixture article generates a valid signal; uncertainty is handled explicitly. 

### **Milestone 4 — Risk API** 

Implementation: Persist raw and processed data; add paginated/filterable article and signal endpoints; add OpenAPI schemas and API tests. 

**Exit criteria:** Frontend/API client can retrieve real stored signals with filters. 

### **Milestone 5 — Portfolio model** 

Implementation: Seed portfolio; define exposure fields, scenario configuration, event mapping, and initial valuation checks. 

**Exit criteria:** Portfolio totals ₹100 crore and model assumptions are documented. 

### **Milestone 6 — Stress engine** 

Implementation: Implement trigger evaluation, idempotency, scenario shocks, valuation, P&L, loss percentage, asset contribution, and persistence. 

**Exit criteria:** Hand-calculated tests pass and asset contributions reconcile. 

### **Milestone 7 — Dashboard** 

Implementation: Build overview, event feed, signal details, portfolio, scenario controls, results, and timeline using backend data. 

**Exit criteria:** Every page has loading, empty, and error states; no fake live values. 

### **Milestone 8 — Integration** 

Implementation: Connect ingestion to NLP, storage, trigger processing, stress tests, and dashboard; add manual demo action. 

**Exit criteria:** One event can be traced end-to-end; duplicate processing does not duplicate runs. 

### **Milestone 9 — Verification** 

Implementation: Run unit/integration tests, linting, frontend type checks, production build, and failure-path tests; fix regressions. 

**Exit criteria:** A repeatable test/demo sequence passes from a clean setup. 

Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

### **Milestone 10 — Submission** 

Implementation: Finish README, environment setup, API docs, architecture diagram, demo script, deployment config, and presentation outline. 

**Exit criteria:** A teammate can follow setup instructions and reproduce the demo. 

## **17. Testing Strategy** 

- Unit tests: normalization, deduplication, sentiment score conversion, event mapping, impact-score bounds, valuation formulas, and rounding. 

- API tests: valid/invalid payloads, pagination, filters, missing records, and database errors. 

- Integration tests: article → signal → trigger → stress run → dashboard data. 

- Idempotency tests: repeated article or signal processing does not create duplicate records/runs. 

- Failure tests: provider timeout, missing credentials, unavailable model, and database failure. 

- Frontend checks: lint, TypeScript type checking, production build, and UI states. 

- Manual acceptance test: run the documented demo workflow from a clean checkout. 

## **18. Suggested 10-Day Schedule** 

|**Schedule**|**Focus**|**Expected result**|
|---|---|---|
|**Day 1**|Foundation|Repository, schemas, database,<br>health checks|
|**Day 2**|Ingestion|Two adapters and deterministic<br>fixtures<br>i|
|**Days 3–4**|NLP|Sentiment, event classification,<br>entity extraction, impact|
|**Day 5**|API|Persistent signals and documented<br>endpoints|
|**Day 6**|Portfolio|Seed positions and scenario<br>assumptions|
|**Day 7**|Stress engine|Revaluation, P&L, asset<br>contribution|
|**Day 8**|Dashboard|Main views connected to backend<br>l|
|**Day 9**|Integration/testing|End-to-end workflow and<br>regression fixes|
|**Day 10**|Submission|Deployment, README, demo,<br>slides|



This schedule is a planning estimate, not a guarantee. Reduce optional features before compromising core functionality or test quality. 

## **19. Five-Minute Demonstration** 

16. 0:00–0:30 — Explain the problem and RiskPulse AI. 

17. 0:30–1:15 — Show the two sources and an incoming article/post. 

18. 1:15–2:00 — Show the entity, sentiment, event type, impact score, and rationale. 

19. 2:00–3:15 — Trigger the stress test; explain the scenario and assumptions. 

20. 3:15–4:15 — Show before/after portfolio valuation and asset-level contribution. 

21. 4:15–5:00 — Explain architecture, validation, and current limitations. 

Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

## **20. Seven-Slide Presentation Outline** 

- Slide 1: Problem, users, and proposed solution. 

- Slide 2: Architecture and data flow. 

- Slide 3: Data sources and NLP pipeline. 

- Slide 4: Risk signal example and model/impact-score explanation. 

- Slide 5: Synthetic portfolio and stress-testing methodology. 

- Slide 6: Dashboard, scenario result, and measured tests. 

- Slide 7: Challenges, limitations, results, and future improvements. 

## **21. Codex Operating Instructions** 

22. Inspect the repository before changing files; preserve useful existing work. 

23. Implement only one milestone at a time. 

24. Before coding, summarize intended changes and identify assumptions. 

25. After coding, run the relevant tests, linting, type checks, and builds. 

26. Fix failures introduced by the implementation before proceeding. 

27. Never claim a feature is complete if it is only a scaffold or mock. 

28. Never replace failed model/API calls with random or fabricated outputs. 

29. Keep demo fixtures visibly distinct from live-source records. 

30. Report changed files, commands run, results, limitations, and the next milestone. 

31. Ask for clarification only when a decision materially blocks implementation; otherwise use documented conservative defaults. 

## **22. Definition of Done** 

- Two independent source adapters exist and their status is visible. 

- Risk signals contain entity, sentiment, event type, impact score, timestamp, and source reference. 

- Signals are persisted and retrievable through the API. 

- The synthetic portfolio starts at exactly ₹100 crore. 

- A qualifying event can trigger a documented scenario. 

- Stress calculations are deterministic, tested, and reconciled at asset and portfolio levels. 

- Dashboard values match backend data. 

- Demo mode works without external credentials and is clearly labeled. 

- Automated checks and production build pass. 

- README and demo instructions allow another developer to run the application. 

- The live demo fits within five minutes and the presentation has no more than seven slides. 

## **Appendix A — Master Prompt for Codex** 

You are the senior engineer building RiskPulse AI according to docs/PROJECT_SPEC.md. 

First inspect the repository and report its current state. Then implement Milestone 1 only. Do not implement all milestones at once. 

For every milestone: 

1. State the intended changes. 

2. Implement the feature using the architecture and data contracts in the specification. 

Hackathon implementation plan • Version 1.0 

RISKPULSE AI  |  PROJECT SPECIFICATION 

3. Add or update tests. 

4. Run relevant tests, linting, type checks, and builds. 

5. Fix failures caused by your changes. 

6. Report modified files, commands run, test results, limitations, and the next milestone. 

Do not overwrite useful existing work. Do not claim unimplemented scaffolding is complete. Do not fabricate live data or random model predictions. Keep demo mode deterministic and visibly distinct from live data. Make financial assumptions explicit and verify calculations with hand-computed tests. Preserve a runnable application after every milestone. 

Begin with repository inspection and Milestone 1 only. 

Hackathon implementation plan • Version 1.0 

