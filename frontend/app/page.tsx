"use client";

import { useEffect, useState } from "react";

type HealthStatus = {
  status: "healthy" | "degraded";
  service: string;
  version: string;
  database: { status: "healthy" | "unavailable" };
};

type NlpStatus = {
  sentiment_backend: string;
  sentiment_model_id: string;
  model_available: boolean;
  pending_articles: number;
  failed_articles: number;
  processed_articles: number;
  signal_count: number;
};

type Signal = {
  id: number;
  article_id: number;
  source: string;
  article_title: string;
  event_type: string;
  sentiment_label: string;
  sentiment_score: number;
  impact_score: number;
  explanation: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [nlpStatus, setNlpStatus] = useState<NlpStatus | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadNlp = async () => {
    const [statusResponse, signalsResponse] = await Promise.all([
      fetch(`${apiUrl}/nlp/status`, { cache: "no-store" }),
      fetch(`${apiUrl}/signals?limit=5`, { cache: "no-store" }),
    ]);
    if (!statusResponse.ok || !signalsResponse.ok) throw new Error("NLP status is unavailable");
    setNlpStatus((await statusResponse.json()) as NlpStatus);
    const signalPage = (await signalsResponse.json()) as { items: Signal[] };
    setSignals(signalPage.items);
  };

  useEffect(() => {
    const load = async () => {
      try {
        const response = await fetch(`${apiUrl}/health`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
        setHealth((await response.json()) as HealthStatus);
        await loadNlp();
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Backend unavailable");
      }
    };
    void load();
  }, []);

  const processPending = async () => {
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/nlp/process-pending`, {
        body: JSON.stringify({ limit: 25 }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      if (!response.ok) throw new Error(`NLP processing returned HTTP ${response.status}`);
      await loadNlp();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "NLP processing failed");
    }
  };

  const status = error ? "degraded" : health?.status ?? "pending";
  const label = status === "pending" ? "Checking" : status === "healthy" ? "Healthy" : "Unavailable";

  return (
    <main className="page">
      <div className="eyebrow">RiskPulse AI · Milestone 3</div>
      <h1>Financial risk intelligence with traceable article signals.</h1>
      <p className="lede">This status view confirms the API, database, and local NLP processing path.</p>

      <section className="status-card" aria-live="polite">
        <div className="status-heading">
          <h2>Environment status</h2>
          <span className={`status-pill ${status}`}>{label}</span>
        </div>
        <div className="status-details">
          {health ? (
            <>
              <div>API service: <strong>{health.service}</strong></div>
              <div>API version: <strong>{health.version}</strong></div>
              <div>PostgreSQL dependency: <strong>{health.database.status}</strong></div>
            </>
          ) : <div>{error ?? "Contacting the backend…"}</div>}
        </div>
      </section>

      <section className="status-card" aria-live="polite">
        <div className="status-heading">
          <h2>NLP pipeline</h2>
          <button className="action-button" onClick={() => void processPending()} type="button">Process pending</button>
        </div>
        {nlpStatus ? (
          <div className="status-details">
            <div>Sentiment backend: <strong>{nlpStatus.sentiment_backend}</strong></div>
            <div>Model configured: <strong>{nlpStatus.sentiment_model_id}</strong></div>
            <div>Pending / failed / processed: <strong>{nlpStatus.pending_articles} / {nlpStatus.failed_articles} / {nlpStatus.processed_articles}</strong></div>
            <div>Persisted signals: <strong>{nlpStatus.signal_count}</strong></div>
          </div>
        ) : <div className="status-details">NLP status is loading.</div>}
      </section>

      <section className="status-card">
        <div className="status-heading"><h2>Recent risk signals</h2></div>
        {signals.length ? (
          <div className="signal-list">
            {signals.map((signal) => (
              <article className="signal" key={signal.id}>
                <div className="signal-meta">{signal.event_type} · impact {signal.impact_score}/10 · {signal.sentiment_label}</div>
                <h3>{signal.article_title}</h3>
                <p>{signal.explanation}</p>
              </article>
            ))}
          </div>
        ) : <p className="note">No signals yet. Load demo articles, then process pending articles.</p>}
      </section>

      <p className="note">Demo fixtures are deterministic and clearly separate from live provider data. Portfolio stress-testing remains outside this milestone.</p>
    </main>
  );
}
