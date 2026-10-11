# Milestone 3 NLP pipeline

The pipeline processes stored `Article` records into one idempotent `RiskSignal` per article:

`Article → preprocessing → conservative entity aliases → sentiment → event rules → impact heuristic → validated persistence`

## Sentiment configuration

`NLP_SENTIMENT_BACKEND=heuristic` is the local default. It uses a deterministic word-list heuristic so tests and demo runs do not download a model. Its probabilities are heuristic estimates and are labelled as such in `model_metadata`.

Set `NLP_SENTIMENT_BACKEND=finbert` to use the optional `ProsusAI/finbert` adapter. Install the optional runtime packages in the backend environment:

```powershell
python -m pip install -r requirements-finbert.txt
$env:NLP_SENTIMENT_BACKEND="finbert"
$env:NLP_ALLOW_MODEL_DOWNLOAD="true"
python -m app.nlp.process --limit 25
```

The adapter loads once per service instance, requests all three labels, and computes `score = P(positive) - P(negative)`. The verified model mapping is positive, negative, neutral. Set `NLP_ALLOW_MODEL_DOWNLOAD=true` only when downloading the model is intended; otherwise a missing local model fails clearly and creates no signal.

The safe default remains `NLP_SENTIMENT_BACKEND=heuristic` with `NLP_ALLOW_MODEL_DOWNLOAD=false`, which is what tests and deterministic demo runs use. FinBERT downloads its model into the local Hugging Face cache on first use; after that, `NLP_ALLOW_MODEL_DOWNLOAD=false` can be used for an offline run.

The official model card documents the model and output labels but does not declare a license. Perform legal review before redistributing or operating FinBERT in a commercial deployment: <https://huggingface.co/ProsusAI/finbert>.

## Entities and events

Entity extraction is alias-driven and intentionally does not invent identifiers. Known aliases are in `backend/data/entity_aliases.json`; the taxonomy supports organizations, central banks, governments, countries, sectors, commodities, currencies, indexes, instruments, and people. Unknown organization-shaped mentions are preserved with `resolved=false` and no invented ticker or identifier.

Detailed event types include `geopolitical`, `macroeconomic`, `credit_event`, `merger_acquisition`, `earnings`, `regulatory`, `product_launch`, `market_crash`, `company_performance`, `liquidity_stress`, `cyber_incident`, `fraud_misconduct`, `litigation`, `operational_disruption`, `climate_risk`, `sovereign_risk`, `currency_shock`, and `other`. Each detailed type also belongs to a broader event group: `market_macro`, `credit_financial`, `corporate_actions`, `regulatory_legal`, `operational_technology`, `climate_esg`, or `other`. Event confidence is rule evidence, not a calibrated model probability.

## Impact score

The score is deterministic and bounded to 1–10:

`round(1 + 9 × (0.60 × event_type_weight + 0.20 × sentiment_magnitude + 0.10 × source_reliability + 0.10 × entity_exposure))`

Sentiment is one float in `[-1, 1]`: FinBERT uses `P(positive) - P(negative)`, while the deterministic heuristic uses the same range. The label and class probabilities are stored as extra metadata. Impact is an integer from 1 to 10. Every persisted signal stores sentiment magnitude, event-type weight, normalized entity exposure, source reliability, and the plain-English rationale.

The repository smoke fixture `backend/tests/fixtures/phrasebank_small.csv` was re-evaluated with the heuristic backend: 3 examples, accuracy `1.0000`, macro-F1 `1.0000`. This is a tiny local check, not a claim about the full Financial PhraseBank; run `python -m research.evaluate_sentiment --config sentences_allagree` after installing the research extras for the full dataset.

## Processing commands and endpoints

```powershell
python -m app.nlp.process --limit 25
python -m app.nlp.process --article-id 1
```

- `GET /nlp/status`
- `POST /nlp/process-pending` with `{"limit":25}`
- `POST /nlp/process/{article_id}`
- `GET /signals?event_type=credit_event&impact_min=5`
- `GET /signals?event_group=credit_financial&impact_min=5`
- `GET /signals/taxonomy`
- `GET /signals/{signal_id}`

Processing states are `pending`, `processing`, `processed`, and `failed`. Failures retain the original article and sanitized error code for retry. A unique article constraint and existing-signal check prevent duplicate signals.

## Limitations

This milestone does not include a portfolio-aware score, live NLP provider, multilingual analysis, a production entity master, a trained event classifier, or stress-testing calculations. API processing endpoints are bounded for local/demo use and do not replace production authentication/rate limiting.
