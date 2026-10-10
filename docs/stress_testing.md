# Stress-testing methodology

RiskPulse AI Milestone 6 is a deterministic educational model. It produces hypothetical portfolio impacts from persisted risk signals and explicit scenario assumptions. It is not a calibrated banking stress framework, a market forecast, or financial advice.

## Eligibility and mapping

A signal qualifies when its impact score is strictly greater than `STRESS_IMPACT_THRESHOLD` (default `7`), its event type maps to an enabled scenario, and portfolio relevance is established. Scores equal to the threshold are rejected. The current mappings are `geopolitical`, `macroeconomic`, `credit_event`, `regulatory`, and `market_crash`. Other NLP event types return `unsupported_event_type` until a validated scenario supports them.

Geopolitical, macroeconomic, and broad-market-crash scenarios are broad-market scenarios. Credit and regulatory scenarios require an exact normalized entity, issuer, borrower, ticker, underlying, or sector relationship. Vague substring matching is not used. A targeted signal with no supported portfolio relationship returns `insufficient_portfolio_relevance`.

## Scenario assumptions

The versioned templates are stored in `app/portfolio/scenarios.py` and persisted in `stress_scenarios`:

- Geopolitical: equity `-10%`, corporate spread `+150 bps`, government yield `-25 bps`, loan PD multiplier `1.5x`.
- Macroeconomic: government and corporate benchmark yields `+200 bps`, corporate spread `+75 bps`, equity `-8%`, loan PD multiplier `1.25x`.
- Credit deterioration: corporate spread `+250 bps`, equity `-5%`, loan PD multiplier `2.0x`.
- Regulatory: relevant equity `-12%`, relevant corporate spread `+100 bps`, relevant loan PD multiplier `1.5x`.
- Broad market crash: equity `-20%`, corporate spread `+200 bps`, loan PD multiplier `1.5x`, government yield `-50 bps`.

These are illustrative assumptions and are not calibrated forecasts.

## Valuation formulas

All monetary values use `Decimal` arithmetic and are rounded half-up to INR paise (`0.01`) at position output and aggregation boundaries.

- Government bonds: `ΔP/P = -D_mod × Δy + 0.5 × Convexity × Δy²` when convexity is available; basis points are divided by `10,000`.
- Corporate bonds: `ΔP/P = -D_rate × Δbenchmark - D_spread × Δspread + convexity(rate)`; benchmark and spread effects are kept separate and spread widening is applied once.
- Corporate loans: `ECL = exposure × PD × LGD`; stressed PD is `min(baseline PD × multiplier, 1)`. P&L is negative incremental ECL, not the full principal exposure.
- Equities: `P&L = market value × return shock`. Beta is recorded as a reference and is not applied twice.
- Derivatives: `P&L = current market value × delta-equivalent × underlying return shock`. Notional is retained for audit but is not treated as market value.

The portfolio convention is `P&L = stressed value - base value`. A negative P&L is a loss. `loss_percentage` is positive for a loss, while `portfolio_return_percentage` follows the signed P&L.

## Persistence and auditability

Each run stores the scenario version, model version, trigger mode, scenario parameters, portfolio and position snapshot, signal snapshot, provenance, warnings, and reconciliation tolerance. Position results store immutable position identifiers, base/stressed values, contribution, inclusion status, calculation method, explanation, and applied shocks.

Automatic or signal-linked triggers use a unique key composed of signal, portfolio, scenario, and version. Repeating a trigger returns the original persisted run. `fresh_run=true` explicitly creates a new run with a unique key. Positions that cannot be modeled are retained at base value, marked `excluded`, and cause a `partial` run with an explanation; they are never silently removed from the denominator.

## API

- `GET /stress-testing/scenarios`
- `POST /stress-testing/run`
- `POST /stress-testing/signals/{signal_id}/run`
- `GET /stress-testing/signals/{signal_id}/eligibility`
- `GET /stress-testing/runs`
- `GET /stress-testing/runs/{simulation_id}`

The frontend uses these endpoints directly. The stress page displays scenario assumptions, high-impact signals, persisted results, position contributions, and reconciliation status. It does not fabricate a result when no simulation exists.

## Limitations

The model is first-order and simplified. It does not model liquidity, correlations, defaults as path-dependent events, accounting provisions, yield-curve shape changes, full derivatives pricing, or regulatory capital. Automatic trigger execution is prepared through the shared eligibility and orchestration service, while ingestion-to-NLP-to-stress background execution remains an integration milestone.
