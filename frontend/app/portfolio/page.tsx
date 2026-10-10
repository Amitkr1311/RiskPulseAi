"use client";

import { useCallback, useEffect, useState } from "react";

import { EmptyState, ErrorState, LoadingState, Metric, PageHeader } from "@/components/ui";
import { api, type Portfolio, type PortfolioPosition } from "@/lib/api";
import { formatInr, formatPercent, titleCase } from "@/lib/format";

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [positions, setPositions] = useState<PortfolioPosition[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [portfolioResponse, positionPage] = await Promise.all([api.getPortfolio(), api.getPortfolioPositions({ limit: 100 })]);
      setPortfolio(portfolioResponse);
      setPositions(positionPage.items);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Portfolio data is unavailable");
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(timer);
  }, [load]);

  if (error && !portfolio) return <ErrorState message={error} retry={() => void load()} />;
  if (!portfolio) return <LoadingState label="Loading portfolio foundation" />;

  return (
    <>
      <PageHeader eyebrow={portfolio.is_demo ? "Synthetic portfolio · hypothetical" : "Persisted portfolio"} title={portfolio.name} description={portfolio.description ?? "Base valuation and allocation view."} actions={<button className="button button-secondary" onClick={() => void load()} type="button">Refresh</button>} />
      {error ? <div className="inline-error" role="status">{error}</div> : null}
      <section className="metrics-grid" aria-label="Portfolio metrics">
        <Metric label="Total market value" value={formatInr(portfolio.total_market_value_crore, "crore")} detail={`${formatInr(portfolio.total_market_value_inr)} INR`} />
        <Metric label="Position count" value={String(portfolio.position_count)} detail="Persisted holdings" />
        <Metric label="Currency" value={portfolio.currency} detail="Canonical money unit" />
        <Metric label="Portfolio type" value={portfolio.is_demo ? "Synthetic demo" : "Persisted portfolio"} detail={portfolio.is_demo ? "Hypothetical holdings" : "User-managed holdings"} />
      </section>

      <div className="two-column-grid portfolio-grid">
        <section className="section-block compact-section">
          <div className="section-heading"><div><div className="section-kicker">Allocation</div><h2>Asset class exposure</h2></div></div>
          <div className="allocation-list">
            {portfolio.asset_class_allocations.map((allocation) => (
              <div className="allocation-row" key={allocation.asset_class}>
                <div className="allocation-label"><span>{titleCase(allocation.asset_class)}</span><strong className="tabular">{formatPercent(allocation.allocation_percentage)}</strong></div>
                <div className="allocation-track"><span style={{ width: `${Number(allocation.allocation_percentage)}%` }} /></div>
                <div className="allocation-value tabular">{formatInr(allocation.market_value_crore, "crore")}</div>
              </div>
            ))}
          </div>
        </section>
        <section className="section-block compact-section">
          <div className="section-heading"><div><div className="section-kicker">Concentration</div><h2>Sector exposure</h2></div></div>
          <div className="allocation-list">
            {portfolio.sector_allocations.map((allocation) => (
              <div className="allocation-row" key={allocation.sector}>
                <div className="allocation-label"><span>{titleCase(allocation.sector)}</span><strong className="tabular">{formatPercent(allocation.allocation_percentage)}</strong></div>
                <div className="allocation-track"><span style={{ width: `${Number(allocation.allocation_percentage)}%` }} /></div>
                <div className="allocation-value tabular">{formatInr(allocation.market_value_inr)}</div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="section-block table-section">
        <div className="section-heading"><div><div className="section-kicker">Holdings</div><h2>Position register</h2></div><span className="table-context">Exact INR values · derived crore display</span></div>
        {positions.length ? <div className="table-wrap"><table className="data-table portfolio-table"><thead><tr><th>Position</th><th>Asset class</th><th>Sector / borrower</th><th>Market value</th><th>Allocation</th><th>Parameters</th></tr></thead><tbody>{positions.map((position) => <tr key={position.id}><td><strong>{position.name}</strong><span className="cell-subtext">{titleCase(position.position_key)}</span></td><td>{titleCase(position.asset_class)}</td><td>{position.sector ?? position.borrower ?? "Not available"}</td><td className="tabular nowrap">{formatInr(position.market_value_crore, "crore")}<span className="cell-subtext">{formatInr(position.market_value_inr)} INR</span></td><td className="tabular">{formatPercent(position.contribution_percentage)}</td><td><details className="parameter-details"><summary>View parameters</summary><dl>{Object.entries(position.valuation_parameters).map(([key, value]) => <div key={key}><dt>{titleCase(key)}</dt><dd className="tabular">{String(value)}</dd></div>)}</dl></details></td></tr>)}</tbody></table></div> : <EmptyState title="No positions available" description="The portfolio API returned no persisted positions." />}
      </section>
    </>
  );
}
