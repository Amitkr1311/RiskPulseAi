"use client";

import { useCallback, useEffect, useState } from "react";

import { ArticleTable } from "@/components/article-table";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/ui";
import { api, type Article, type IngestionStatus, type RiskSignal } from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";

const pageSize = 25;

export default function NewsPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const [ingestion, setIngestion] = useState<IngestionStatus | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [source, setSource] = useState("");
  const [processingStatus, setProcessingStatus] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [articlePage, signalPage, status] = await Promise.all([
        api.getArticles({ limit: pageSize, offset, source: source || undefined, processing_status: processingStatus || undefined, search: search || undefined }),
        api.getSignals({ limit: 100, source: source || undefined }),
        api.getIngestionStatus(),
      ]);
      setArticles(articlePage.items);
      setTotal(articlePage.total);
      setSignals(signalPage.items);
      setIngestion(status);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "News feed is unavailable");
    } finally {
      setLoading(false);
    }
  }, [offset, processingStatus, search, source]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 15_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const signalsByArticle = new Map(signals.map((signal) => [signal.article_id, signal]));
  const clearFilters = () => {
    setSource("");
    setProcessingStatus("");
    setSearch("");
    setOffset(0);
  };

  return (
    <>
      <PageHeader eyebrow="RSS, social and Reddit intelligence" title="News Feed" description="Unified source records with publication time, ingestion time, processing state, and linked risk output." actions={<button className="button button-secondary" onClick={() => void load()} type="button">Refresh</button>} />
      <section className="filter-panel" aria-label="News filters">
        <label>Source<select onChange={(event) => { setSource(event.target.value); setOffset(0); }} value={source}><option value="">All sources</option><option value="news">RSS</option><option value="social">Social replay</option><option value="reddit">Reddit</option></select></label>
        <label>Processing<select onChange={(event) => { setProcessingStatus(event.target.value); setOffset(0); }} value={processingStatus}><option value="">All states</option><option value="pending">Pending</option><option value="processing">Processing</option><option value="processed">Processed</option><option value="failed">Failed</option></select></label>
        <label className="filter-search">Search title or text<input onChange={(event) => { setSearch(event.target.value); setOffset(0); }} placeholder="Search articles" value={search} /></label>
        <button className="button button-quiet" onClick={clearFilters} type="button">Clear filters</button>
      </section>

      <section className="source-health-grid" aria-label="Source health">
        {ingestion?.sources.map((sourceStatus) => {
          const run = sourceStatus.enabled ? sourceStatus.last_run : null;
          const statusText = !sourceStatus.enabled ? "Disabled" : sourceStatus.configured ? "Configured" : "Not configured";
          const statusClass = !sourceStatus.enabled ? "muted" : sourceStatus.configured ? "positive" : "muted";
          const sourceLabel = sourceStatus.source === "news" ? "RSS" : sourceStatus.source === "social" ? "Social replay" : "Reddit";
          return <div className="source-health" key={sourceStatus.source}><div className="source-health-heading"><strong>{sourceLabel}</strong><span className={"status-label " + statusClass}>{statusText}</span></div><div className="source-health-detail">Last run: {run ? titleCase(run.status) + " · " + formatDate(run.completed_at) : "Not available"}</div><div className="source-health-detail">Fetched <strong className="tabular">{run?.records_seen ?? 0}</strong> · inserted <strong className="tabular">{run?.records_created ?? 0}</strong> · duplicates <strong className="tabular">{run?.duplicates_skipped ?? 0}</strong>{run?.records_failed ? ` · failed ${run.records_failed}` : ""}{run?.error_category ? " · " + titleCase(run.error_category) : ""}</div></div>;
        }) ?? <div className="state-panel">Source health is loading.</div>}
      </section>

      {error ? <ErrorState message={error} retry={() => void load()} /> : loading && !articles.length ? <LoadingState label="Loading article feed" /> : (
        <section className="section-block table-section">
          <div className="section-heading"><div><div className="section-kicker">Collected records</div><h2>{total} article{total === 1 ? "" : "s"}</h2></div><span className="table-context">Showing {total ? offset + 1 : 0}–{Math.min(offset + pageSize, total)} of {total}</span></div>
          {articles.length ? <ArticleTable articles={articles} signalsByArticle={signalsByArticle} /> : <EmptyState title="No articles match the filters" description="When a configured RSS, social replay, or Reddit source is ingested, records will appear here." />}
          <div className="pagination"><button className="button button-quiet" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))} type="button">← Previous</button><span className="tabular">Page {Math.floor(offset / pageSize) + 1} of {Math.max(1, Math.ceil(total / pageSize))}</span><button className="button button-quiet" disabled={offset + pageSize >= total} onClick={() => setOffset(offset + pageSize)} type="button">Next →</button></div>
        </section>
      )}
    </>
  );
}
