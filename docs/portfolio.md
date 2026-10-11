# Portfolio foundation

## Transaction-derived synthetic input

`data/transactions.csv` is a consumer transaction export, not a bank wholesale portfolio. `scripts/build_portfolio.py` validates its `Date` and `Amount` fields, ignores non-debit rows for spending proxies, removes exact duplicate rows, groups by `Category` plus `Description` (the merchant-like field in this export), and maps category text to broad sectors such as utilities, transportation, consumer staples, financials, and real-estate services. Recurring groups inform the label and sector of a synthetic loan-exposure proxy; the data does not prove that a loan exists.

The remaining government-bond, corporate-bond, equity, and derivative positions are clearly labelled synthetic allocations required by the case-study portfolio. The generated seed remains exactly ₹100 crore: 40% synthetic loan proxy, 25% government bonds, 20% corporate bonds, 10% equities, and 5% derivatives. Derivative notional is stored separately from marked-to-market value, and the four derivative positions retain their tenor, fixed/floating rate, pay/receive, FX pair, and forward/spot fields.

The portfolio is deterministic and synthetic for local development. Its base valuation is database-backed and is consumed by the scenario, signal-relevance, and stress-testing services; the consumer transaction export informs labels and sector proxies but does not become a claimed wholesale holding book.

## Demo portfolio

The seed is stable and idempotent:

- Portfolio key: `demo-banking-portfolio`
- Name: `Demo Banking Portfolio`
- Currency: `INR`
- Total market value: `₹1,000,000,000.00` (`₹100.00 crore`)
- Positions: exactly five

| Asset class | Market value (INR) | Market value (crore) | Allocation |
| --- | ---: | ---: | ---: |
| Corporate loans | 400,000,000.00 | 40.00 | 40% |
| Government bonds | 250,000,000.00 | 25.00 | 25% |
| Corporate bonds | 200,000,000.00 | 20.00 | 20% |
| Equities | 100,000,000.00 | 10.00 | 10% |
| Derivatives | 50,000,000.00 | 5.00 | 5% |

The API uses exact Decimal values and exposes rupees as `market_value_inr`. Crore values are derived for display using `₹1 crore = ₹10,000,000`; they are not independently stored. Derivative market values are simplified marked-to-market values, while each derivative keeps its notional, tenor, and rate/FX terms in `valuation_parameters`.

## Base valuation formulas

Milestone 5 reports holdings, totals, asset-class allocation, sector allocation, and position contribution. It does not apply any shock.

- Allocation percentage = `position or group market value / total portfolio market value × 100`.
- Interest-rate approximation for a later stress milestone: `ΔP/P ≈ -D_mod × Δy`. If convexity is supplied, a later implementation may add `0.5 × Convexity × (Δy)^2`.
- `100 bps = 0.01` as an absolute decimal rate change.
- Expected credit loss for a later credit-stress implementation: `ECL = Exposure × PD × LGD`.
- Equity return approximation: `ΔV = Market Value × Return Shock`. Apply beta once when the scenario explicitly represents a broad-market return shock.
- Interest-rate swaps use `ΔV ≈ Notional × Duration × Rate Shock` with rate shocks converted from basis points.
- FX forwards use `ΔV ≈ Notional × FX Shock`.

All rate, return, spread, PD, LGD, recovery, duration, beta, and derivative sensitivity units are explicit in the position parameters and scenario templates. Beta is an exposure sensitivity and is not constrained to the `[0, 1]` interval.

## Scenario templates

The demo portfolio contains two interest-rate swaps and two FX forwards alongside loans, bonds, and equities. It also contains named Tesla, Apple, Microsoft, and HDFC Bank loan, bond, and equity exposures. Their issuer, borrower, sector, and ticker fields are deliberately explicit so a signal entity can be matched to the relevant positions. Five deterministic, validated templates are defined in `backend/app/portfolio/scenarios.py`: geopolitical, macroeconomic/rate, credit event, regulatory, and market crash. The stress engine applies the simplified derivative shocks to every included derivative position.

## API

- `GET /portfolio` — demo portfolio metadata and totals.
- `GET /portfolio/positions` — paginated positions, with optional `asset_class` and `sector` filters.
- `GET /portfolio/positions/{position_id}` — one position and its validated parameters.
- `GET /portfolio/summary` — totals, counts, asset-class allocations, sector allocations, and position contributions.

The seed command does not overwrite existing portfolio or position records. It creates only missing demo records, so user changes are preserved.
