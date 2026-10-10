"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { RiskSignalTable, SignalArticleLink } from "@/components/risk-signal-table";
import { EmptyState, ErrorState, ImpactMark, LoadingState, PageHeader } from "@/components/ui";
import { api, type RiskSignal, type SignalTaxonomy } from "@/lib/api";
import { formatDate, formatPercent, titleCase } from "@/lib/format";

const pageSize = 20;

export default function SignalsPage() {
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<RiskSignal | null>(null);
  const [taxonomy, setTaxonomy] = useState<SignalTaxonomy | null>(null);
  const [entity, setEntity] = useState("");
  const [eventType, setEventType] = useState("");
  const [eventGroup, setEventGroup] = useState("");
  const [source, setSource] = useState("");
  const [sentiment, setSentiment] = useState("");
  const [impactMin, setImpactMin] = useState("");
  const [sort, setSort] = useState("recent");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [response, taxonomyResponse] = await Promise.all([
        api.getSignals({
          limit: pageSize,
          offset,
          entity: entity || undefined,
          event_type: eventType || undefined,
          event_group: eventGroup || undefined,
          source: source || undefined,
          sentiment_label: sentiment || undefined,
          impact_min: impactMin ? Number(impactMin) : undefined,
        }),
        api.getSignalTaxonomy(),
      ]);
      setSignals(response.items);
      setTotal(response.total);
      setTaxonomy(taxonomyResponse);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Signals are unavailable");
    } finally {
      setLoading(false);
    }
  }, [entity, eventGroup, eventType, impactMin, offset, sentiment, source]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 15_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const displayedSignals = useMemo(
    () => sort === "impact" ? [...signals].sort((a, b) => b.impact_score - a.impact_score || b.created_at.localeCompare(a.created_at)) : signals,
    [signals, sort],
  );

  const clearFilters = () => {
    setEntity("");
    setEventType("");
    setEventGroup("");
    setSource("");
    setSentiment("");
    setImpactMin("");
    setOffset(0);
  };

  return (
    <>
      <PageHeader eyebrow="Traceable NLP output" title="Risk Signals" description="Review persisted event classifications, impact scores, sentiment, and model rationale from the ingestion pipeline." actions={<button className="button button-secondary" onClick={() => void load()} type="button">Refresh</button>} />
      <section className="filter-panel" aria-label="Risk signal filters">
        <label>Entity<input onChange={(event) => { setEntity(event.target.value); setOffset(0); }} placeholder="Search entity" value={entity} /></label>
        <label>Event group<select onChange={(event) => { setEventGroup(event.target.value); setOffset(0); }} value={eventGroup}><option value="">All event groups</option>{Object.keys(taxonomy?.event_groups ?? {}).map((group) => <option key={group} value={group}>{titleCase(group)}</option>)}</select></label>
        <label>Event type<select onChange={(event) => { setEventType(event.target.value); setOffset(0); }} value={eventType}><option value="">All event types</option>{(taxonomy?.event_types ?? []).filter((type) => type !== "other").map((type) => <option key={type} value={type}>{titleCase(type)}</option>)}<option value="other">Other</option></select></label>
        <label>Source<select onChange={(event) => { setSource(event.target.value); setOffset(0); }} value={source}><option value="">All sources</option><option value="news">RSS</option><option value="reddit">Reddit</option></select></label>
        <label>Sentiment<select onChange={(event) => { setSentiment(event.target.value); setOffset(0); }} value={sentiment}><option value="">All sentiment</option><option value="negative">Negative</option><option value="neutral">Neutral</option><option value="positive">Positive</option></select></label>
        <label>Minimum impact<select onChange={(event) => { setImpactMin(event.target.value); setOffset(0); }} value={impactMin}><option value="">Any score</option>{[1, 4, 6, 8].map((score) => <option key={score} value={score}>{score}/10 and above</option>)}</select></label>
        <label>Sort<select onChange={(event) => setSort(event.target.value)} value={sort}><option value="recent">Most recent</option><option value="impact">Highest impact</option></select></label>
        <button className="button button-quiet" onClick={clearFilters} type="button">Clear filters</button>
      </section>

      {error ? <ErrorState message={error} retry={() => void load()} /> : loading && !signals.length ? <LoadingState label="Loading persisted signals" /> : (
        <section className="section-block table-section">
          <div className="section-heading"><div><div className="section-kicker">Signal register</div><h2>{total} persisted signal{total === 1 ? "" : "s"}</h2></div><span className="table-context">Showing {total ? offset + 1 : 0}–{Math.min(offset + pageSize, total)} of {total}</span></div>
          {displayedSignals.length ? <RiskSignalTable signals={displayedSignals} onSelect={setSelected} /> : <EmptyState title="No matching signals" description="Try clearing one or more filters, or process pending articles from the overview." />}
          <Pagination offset={offset} total={total} onChange={setOffset} />
        </section>
      )}

      {selected ? <SignalDetail signal={selected} onClose={() => setSelected(null)} /> : null}
    </>
  );
}

function Pagination({ offset, total, onChange }: { offset: number; total: number; onChange: (offset: number) => void }) {
  return (
    <div className="pagination">
      <button className="button button-quiet" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - pageSize))} type="button">← Previous</button>
      <span className="tabular">Page {Math.floor(offset / pageSize) + 1} of {Math.max(1, Math.ceil(total / pageSize))}</span>
      <button className="button button-quiet" disabled={offset + pageSize >= total} onClick={() => onChange(offset + pageSize)} type="button">Next →</button>
    </div>
  );
}

function SignalDetail({ signal, onClose }: { signal: RiskSignal; onClose: () => void }) {
  return (
    <div className="detail-overlay" role="dialog" aria-label="Risk signal detail" aria-modal="true">
      <button className="detail-backdrop" aria-label="Close signal detail" onClick={onClose} type="button" />
      <aside className="detail-panel">
        <div className="detail-header"><div><div className="section-kicker">Signal {signal.id}</div><h2>{signal.article_title}</h2></div><button className="button button-quiet" onClick={onClose} type="button">Close</button></div>
        <div className="detail-impact"><ImpactMark score={signal.impact_score} /><span className="tabular">Confidence {signal.event_confidence === null ? "Not available" : formatPercent(signal.event_confidence * 100)}</span></div>
        <dl className="detail-list">
          <div><dt>Event type</dt><dd>{titleCase(signal.event_type)}</dd></div>
          <div><dt>Sentiment</dt><dd>{signal.sentiment_label ?? "Not available"} <span className="tabular">({signal.sentiment_score.toFixed(2)})</span></dd></div>
          <div><dt>Entities</dt><dd>{signal.entities.length ? signal.entities.map((entity) => entity.canonical_name).join(", ") : "Unresolved"}</dd></div>
          <div><dt>Model</dt><dd>{signal.model_version}</dd></div>
          <div><dt>Detected</dt><dd className="tabular">{formatDate(signal.created_at)}</dd></div>
          <div><dt>Published</dt><dd className="tabular">{formatDate(signal.article.published_at)}</dd></div>
          <div><dt>Ingested</dt><dd className="tabular">{formatDate(signal.article.ingested_at)}</dd></div>
        </dl>
        <div className="detail-copy"><div className="section-kicker">Scoring rationale</div><p>{signal.explanation}</p></div>
        <div className="detail-copy"><div className="section-kicker">Source</div><p><SignalArticleLink signal={signal} /></p></div>
      </aside>
    </div>
  );
}
