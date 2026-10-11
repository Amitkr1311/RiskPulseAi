"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ArticleTable } from "@/components/article-table";
import { EmptyState, ErrorState, LoadingState, PageHeader, RefreshButton } from "@/components/ui";
import { api, type Article, type IngestionStatus, type RiskSignal, type SocialReplayStatus } from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";

const pageSize = 25;

export default function NewsPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const [ingestion, setIngestion] = useState<IngestionStatus | null>(null);
  const [replay, setReplay] = useState<SocialReplayStatus | null>(null);
  const [replaySpeed, setReplaySpeed] = useState(1);
  const [replayBatchSize, setReplayBatchSize] = useState(1);
  const [replayAction, setReplayAction] = useState<string | null>(null);
  const [replayError, setReplayError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [source, setSource] = useState("");
  const [processingStatus, setProcessingStatus] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const replayPositionRef = useRef<number | null>(null);
  const lastFeedRefreshRef = useRef(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [articlePage, signalPage, status, replayStatus] = await Promise.all([
        api.getArticles({ limit: pageSize, offset, source: source || undefined, processing_status: processingStatus || undefined, search: search || undefined }),
        api.getSignals({ limit: 100, source: source || undefined }),
        api.getIngestionStatus(),
        api.getReplayStatus(),
      ]);
      setArticles(articlePage.items);
      setTotal(articlePage.total);
      setSignals(signalPage.items);
      setIngestion(status);
      setReplay(replayStatus);
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

  useEffect(() => {
    const pollReplay = async () => {
      try {
        const next = await api.getReplayStatus();
        const previousPosition = replayPositionRef.current;
        replayPositionRef.current = next.current_position;
        setReplay(next);
        if (previousPosition !== null && previousPosition !== next.current_position && Date.now() - lastFeedRefreshRef.current > 4_000) {
          lastFeedRefreshRef.current = Date.now();
          void load();
        }
      } catch (requestError) {
        setReplayError(requestError instanceof Error ? requestError.message : "Replay status is unavailable");
      }
    };
    void pollReplay();
    const timer = window.setInterval(() => void pollReplay(), 2_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const signalsByArticle = new Map(signals.map((signal) => [signal.article_id, signal]));
  const clearFilters = () => {
    setSource("");
    setProcessingStatus("");
    setSearch("");
    setOffset(0);
  };

  async function runReplayAction(action: "start" | "pause" | "resume" | "stop" | "reset") {
    setReplayAction(action);
    setReplayError(null);
    try {
      const next = action === "start"
        ? await api.startReplay({ speed_records_per_second: replaySpeed, batch_size: replayBatchSize })
        : await api[`${action}Replay` as "pauseReplay" | "resumeReplay" | "stopReplay" | "resetReplay"]();
      setReplay(next);
      replayPositionRef.current = next.current_position;
      await load();
    } catch (requestError) {
      setReplayError(requestError instanceof Error ? requestError.message : "Replay action failed");
    } finally {
      setReplayAction(null);
    }
  }

  const replayBusy = replayAction !== null;
  const replayStatus = replay?.status ?? "idle";

  return (
    <>
      <PageHeader eyebrow="RSS, social and Reddit intelligence" title="News Feed" description="Unified source records with publication time, ingestion time, processing state, and linked risk output." actions={<RefreshButton onRefresh={load} />} />
      <section className="section-block replay-panel" aria-labelledby="social-replay-heading">
        <div className="section-heading"><div><div className="section-kicker">Historical data stream</div><h2 id="social-replay-heading">Social replay</h2></div><span className={"status-label " + (replayStatus === "running" ? "positive" : "muted")}>{titleCase(replayStatus)}</span></div>
        <p className="section-copy">Replays the downloaded historical CSV through the same article, NLP, risk-signal, and qualifying stress-test pipeline. Records remain labelled historical; this is not a live social feed.</p>
        <div className="replay-controls">
          <label className="field-label">Speed<select disabled={replayBusy || replayStatus === "running" || replayStatus === "paused"} onChange={(event) => setReplaySpeed(Number(event.target.value))} value={replaySpeed}><option value={1}>1 record/sec</option><option value={5}>5 records/sec</option><option value={10}>10 records/sec</option></select></label>
          <label className="field-label">Batch size<select disabled={replayBusy || replayStatus === "running" || replayStatus === "paused"} onChange={(event) => setReplayBatchSize(Number(event.target.value))} value={replayBatchSize}><option value={1}>1 record</option><option value={5}>5 records</option><option value={10}>10 records</option><option value={25}>25 records</option></select></label>
          <div className="replay-buttons">
            <button className="button button-primary" disabled={replayBusy || replayStatus === "running" || replayStatus === "paused" || !replay?.configured} onClick={() => void runReplayAction("start")} type="button">Start</button>
            <button className="button button-quiet" disabled={replayBusy || replayStatus !== "running"} onClick={() => void runReplayAction("pause")} type="button">Pause</button>
            <button className="button button-quiet" disabled={replayBusy || replayStatus !== "paused"} onClick={() => void runReplayAction("resume")} type="button">Resume</button>
            <button className="button button-quiet" disabled={replayBusy || (replayStatus !== "running" && replayStatus !== "paused")} onClick={() => void runReplayAction("stop")} type="button">Stop</button>
            <button className="button button-secondary" disabled={replayBusy || replayStatus === "running" || replayStatus === "paused"} onClick={() => void runReplayAction("reset")} type="button">Reset</button>
          </div>
        </div>
        <div className="replay-progress" aria-label={`Replay progress ${replay?.progress_percentage ?? 0}%`}><span style={{ width: `${replay?.progress_percentage ?? 0}%` }} /></div>
        <div className="replay-metrics"><span><strong>{replay?.records_attempted ?? 0}</strong> / {replay?.total_records ?? 0} attempted</span><span><strong>{replay?.records_inserted ?? 0}</strong> inserted</span><span><strong>{replay?.duplicates_skipped ?? 0}</strong> duplicates</span><span><strong>{replay?.records_failed ?? 0}</strong> failed</span></div>
        <div className="replay-meta">Dataset: <strong>{replay?.dataset ?? "Not configured"}</strong>{replay?.last_record_at ? <> · Last historical timestamp: <strong>{formatDate(replay.last_record_at)}</strong></> : null}{replay?.last_error ? <span className="inline-error">{replay.last_error}</span> : null}{replayError ? <span className="inline-error">{replayError}</span> : null}</div>
      </section>
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
