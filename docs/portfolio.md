# Portfolio foundation

Milestone 5 establishes a deterministic synthetic portfolio for local development. It provides base valuation and allocation data only; scenario triggers, stress calculations, stressed P&L, signal mapping, and portfolio-aware risk scores are deferred to later milestones.

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

The demo portfolio contains two interest-rate swaps and two FX forwards alongside loans, bonds, and equities. Five deterministic, validated templates are defined in `backend/app/portfolio/scenarios.py`: geopolitical, macroeconomic/rate, credit event, regulatory, and market crash. The stress engine applies the simplified derivative shocks to every included derivative position.

## API

- `GET /portfolio` — demo portfolio metadata and totals.
- `GET /portfolio/positions` — paginated positions, with optional `asset_class` and `sector` filters.
- `GET /portfolio/positions/{position_id}` — one position and its validated parameters.
- `GET /portfolio/summary` — totals, counts, asset-class allocations, sector allocations, and position contributions.

The seed command does not overwrite existing portfolio or position records. It creates only missing demo records, so user changes are preserved.
