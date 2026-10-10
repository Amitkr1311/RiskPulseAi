"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ArticleTable } from "@/components/article-table";
import { RiskSignalTable } from "@/components/risk-signal-table";
import { EmptyState, ErrorState, LoadingState, Metric, PageHeader } from "@/components/ui";
import { api, type Article, type DashboardSummary, type IngestionStatus, type PortfolioSummary, type RiskSignal } from "@/lib/api";
import { formatDate, formatInr, formatPercent, titleCase } from "@/lib/format";

type OverviewData = {
  summary: DashboardSummary;
  signals: RiskSignal[];
  articles: Article[];
  portfolio: PortfolioSummary;
  ingestion: IngestionStatus;
};

export default function OverviewPage() {
  const router = useRouter();
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [summary, signals, articles, portfolio, ingestion] = await Promise.all([
        api.getDashboardSummary(),
        api.getSignals({ limit: 8, impact_min: 1 }),
        api.getArticles({ limit: 8 }),
        api.getPortfolioSummary(),
        api.getIngestionStatus(),
      ]);
      setData({ summary, signals: signals.items, articles: articles.items, portfolio, ingestion });
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Overview data is unavailable");
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 15_000);
    return () => window.clearInterval(timer);
  }, [load]);

  if (error && !data) return <ErrorState message={error} retry={() => void load()} />;
  if (!data) return <LoadingState label="Loading risk overview" />;

  const signalsByArticle = new Map(data.signals.map((signal) => [signal.article_id, signal]));

  return (
    <>
      <PageHeader
        eyebrow="Risk intelligence workspace"
        title="Overview"
        description="A current view of the information stream, material risk signals, and synthetic portfolio exposure."
        actions={<button className="button button-secondary" onClick={() => void load()} type="button">Refresh data</button>}
      />
      {error ? <div className="inline-error" role="status">{error}</div> : null}

      <section className="metrics-grid" aria-label="Key metrics">
        <Metric label="Articles ingested" value={String(data.summary.total_articles)} detail={`${data.summary.live_articles} live · ${data.summary.demo_articles} demo`} />
        <Metric label="Risk signals" value={String(data.summary.total_signals)} detail={`${data.summary.recent_signal_counts.last_24_hours} detected in 24h`} />
        <Metric label="High-impact events" value={String(data.summary.high_impact_signals)} detail={`Impact threshold ≥ ${data.summary.high_impact_threshold}`} />
        <Metric label="Portfolio value" value={formatInr(data.portfolio.total_market_value_crore, "crore")} detail={data.portfolio.is_demo ? "Synthetic demo portfolio" : "Persisted portfolio"} />
      </section>

      <section className="section-block">
        <div className="section-heading"><div><div className="section-kicker">Priority queue</div><h2>Highest-priority risk signals</h2></div><Link className="text-link" href="/signals">View all signals →</Link></div>
        {data.signals.length ? <RiskSignalTable signals={[...data.signals].sort((a, b) => b.impact_score - a.impact_score)} onSelect={() => router.push("/signals")} /> : <EmptyState title="No risk signals yet" description="Signals will appear after live or demo articles are processed by the NLP pipeline." />}
      </section>

      <div className="two-column-grid">
        <section className="section-block compact-section">
          <div className="section-heading"><div><div className="section-kicker">Information stream</div><h2>Recent financial news</h2></div><Link className="text-link" href="/news">Open news feed →</Link></div>
          <ArticleTable articles={data.articles.slice(0, 5)} signalsByArticle={signalsByArticle} />
        </section>
        <section className="section-block compact-section">
          <div className="section-heading"><div><div className="section-kicker">Exposure</div><h2>Portfolio allocation</h2></div><Link className="text-link" href="/portfolio">Open portfolio →</Link></div>
          <div className="allocation-list">
            {data.portfolio.asset_class_allocations.map((allocation) => (
              <div className="allocation-row" key={allocation.asset_class}>
                <div className="allocation-label"><span>{titleCase(allocation.asset_class)}</span><strong className="tabular">{formatPercent(allocation.allocation_percentage)}</strong></div>
                <div className="allocation-track"><span style={{ width: `${Number(allocation.allocation_percentage)}%` }} /></div>
                <div className="allocation-value tabular">{formatInr(allocation.market_value_crore, "crore")}</div>
              </div>
            ))}
          </div>
          <div className="assumption-note">{data.portfolio.is_demo ? "Hypothetical synthetic portfolio. Base valuation only; no stress result is available." : "Persisted portfolio valuation. Base valuation only."}</div>
        </section>
      </div>

      <section className="section-block">
        <div className="section-heading"><div><div className="section-kicker">Methodology boundary</div><h2>Stress-test status</h2></div><Link className="text-link" href="/stress-testing">Open stress testing →</Link></div>
        <div className="status-strip">
          <div><span className="status-dot" aria-hidden="true" /><strong>No completed simulation</strong><span className="cell-subtext">No stress-test result is available in this release.</span></div>
          <div className="status-strip-meta">Last ingestion: <strong className="tabular">{formatDate(data.summary.latest_ingestion_at)}</strong><br />Last NLP processing: <strong className="tabular">{formatDate(data.summary.latest_processed_at)}</strong></div>
        </div>
      </section>
    </>
  );
}
