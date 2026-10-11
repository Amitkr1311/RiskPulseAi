# Research integrations

Research integrations are deliberately separate from live RSS articles, persisted risk signals, the synthetic portfolio, and stress-test runs. They do not run during application startup or dashboard refreshes.

## Financial PhraseBank evaluation

The evaluator uses the existing `HeuristicSentimentAnalyzer` by default, or the configured FinBERT adapter when `NLP_SENTIMENT_BACKEND=finbert`. It does not train or fine-tune either model.

The default dataset configuration is `sentences_allagree`. Other Hugging Face configurations include `sentences_75agree`, `sentences_66agree`, and `sentences_50agree`. The dataset is `takala/financial_phrasebank` and is licensed `CC-BY-NC-SA-3.0`; review the license before commercial redistribution.

Install the optional loader and run the evaluation from `backend`:

```powershell
python -m pip install -r requirements-research.txt
python -m research.evaluate_sentiment --config sentences_allagree
```

The command requires network access for the first Hugging Face dataset download. It writes:

- `backend/research/reports/financial_phrasebank_latest.json`
- `backend/research/reports/financial_phrasebank_latest.txt`

To evaluate a locally prepared CSV, JSON, or JSONL file without downloading the dataset:

```powershell
python -m research.evaluate_sentiment --local-path C:\path\to\phrasebank.csv
```

CSV records must contain `sentence` and `label` columns. Labels may be `negative`, `neutral`, `positive`, or `-1`, `0`, `1`. The report includes accuracy, macro-F1, per-class precision/recall/F1, confusion matrix, class distribution, dataset configuration, model identifier, evaluation date, and limitations. If the dataset, model, or optional loader is unavailable, the command exits with an explicit `EVALUATION SKIPPED` message and does not create fabricated metrics.

PhraseBank is a sentence-level benchmark and does not represent the full structure of long news articles. The evaluation measures classification behavior; it does not demonstrate trading performance or causal market prediction.

## Historical market data

The optional utility uses `yfinance.download` with an explicit daily `auto_adjust=True` convention, a configurable symbol, an inclusive start date, and an exclusive end date. yfinance and Yahoo Finance data are subject to their applicable terms and intended-use restrictions. See the [yfinance documentation](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html) and Yahoo Finance terms before use.

Download a research CSV:

```powershell
python -m research.market_research download `
  --symbol "^GSPC" `
  --start 2024-01-01 `
  --end 2024-12-31 `
  --output research/market_data/sp500_2024.csv
```

Compare an event date with 1-, 5-, and 20-trading-day forward windows:

```powershell
python -m research.market_research event-window `
  --symbol "^GSPC" `
  --start 2024-01-01 `
  --end 2024-12-31 `
  --event-date 2024-03-11 `
  --event-category market_crash `
  --scenario-name "Broad market crash" `
  --assumed-shock -0.10 `
  --windows 1,5,20
```

The event-window output preserves the original event date, records the mapped trading date, and reports observed return, assumed shock, and observed-minus-assumed difference separately. A weekend or holiday maps to the next available trading date explicitly; it is not silently treated as the event date. The utility handles empty responses, missing prices, duplicate dates, invalid symbols, and provider failures.

Historical equity or index prices are market proxies only. They do not validate government-bond duration, corporate credit spreads, PD/LGD, derivatives pricing, or the synthetic banking portfolio. No scenario shock is automatically recalibrated from a historical return, and the output makes no causal claim.

## Research API and frontend

- `GET /research/sentiment-evaluation` returns the local report when one exists, otherwise an unavailable state.
- `GET /research/market-data?symbol=^GSPC&start=2024-01-01&end=2024-12-31` explicitly retrieves historical prices.
- `GET /research/event-window?...` explicitly retrieves prices and calculates event-window comparisons.

The frontend Research page does not download data automatically. It separates offline sentiment evaluation, historical market research, live RSS status, and hypothetical stress-test results.
