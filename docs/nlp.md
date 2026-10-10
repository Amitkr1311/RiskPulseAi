# Milestone 3 NLP pipeline

The pipeline processes stored `Article` records into one idempotent `RiskSignal` per article:

`Article → preprocessing → conservative entity aliases → sentiment → event rules → impact heuristic → validated persistence`

## Sentiment configuration

`NLP_SENTIMENT_BACKEND=heuristic` is the local default. It uses a deterministic word-list heuristic so tests and demo runs do not download a model. Its probabilities are heuristic estimates and are labelled as such in `model_metadata`.

Set `NLP_SENTIMENT_BACKEND=finbert` to use the optional `ProsusAI/finbert` adapter. Install the optional runtime packages in the backend environment:

```powershell
python -m pip install transformers torch
```

The adapter loads once per service instance, requests all three labels, and computes `score = P(positive) - P(negative)`. The verified model mapping is positive, negative, neutral. Set `NLP_ALLOW_MODEL_DOWNLOAD=true` only when downloading the model is intended; otherwise a missing local model fails clearly and creates no signal.

The official model card documents the model and output labels but does not declare a license. Perform legal review before redistributing or operating FinBERT in a commercial deployment: <https://huggingface.co/ProsusAI/finbert>.

## Entities and events

Entity extraction is deliberately conservative. Known aliases are in `backend/data/entity_aliases.json`; an unknown organization-shaped mention is preserved with `resolved=false` and no invented ticker or identifier. Event categories are `geopolitical`, `macroeconomic`, `credit_event`, `merger_acquisition`, `earnings`, `regulatory`, `product_launch`, `market_crash`, `company_performance`, and `other`. Event confidence is rule evidence, not a calibrated model probability.

## Impact score

The score is deterministic and bounded to 1–10:

`round(1 + 9 × (0.65 × severity + 0.20 × |sentiment_score| + 0.15 × source_reliability))`

Severity and source-reliability tables are in `app/nlp/impact.py`. Every persisted signal stores the factor breakdown and rationale. Portfolio relevance is explicitly not assessed until stress testing.

## Processing commands and endpoints

```powershell
python -m app.nlp.process --limit 25
python -m app.nlp.process --article-id 1
```

- `GET /nlp/status`
- `POST /nlp/process-pending` with `{"limit":25}`
- `POST /nlp/process/{article_id}`
- `GET /signals?event_type=credit_event&impact_min=5`
- `GET /signals/{signal_id}`

Processing states are `pending`, `processing`, `processed`, and `failed`. Failures retain the original article and sanitized error code for retry. A unique article constraint and existing-signal check prevent duplicate signals.

## Limitations

This milestone does not include a portfolio-aware score, live NLP provider, multilingual analysis, a production entity master, a trained event classifier, or stress-testing calculations. API processing endpoints are bounded for local/demo use and do not replace production authentication/rate limiting.
