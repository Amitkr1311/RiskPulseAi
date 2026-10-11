"use client";

import { useEffect, useState } from "react";

import { EmptyState, ErrorState, PageHeader } from "@/components/ui";
import { api, type EventWindowResearchResponse, type SentimentEvaluationReport } from "@/lib/api";
import { formatDate, formatPercent, titleCase } from "@/lib/format";

export default function ResearchPage() {
  const [evaluation, setEvaluation] = useState<SentimentEvaluationReport | null>(null);
  const [evaluationMessage, setEvaluationMessage] = useState("Loading evaluation status");
  const [evaluationError, setEvaluationError] = useState<string | null>(null);
  const [market, setMarket] = useState<EventWindowResearchResponse | null>(null);
  const [marketError, setMarketError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [symbol, setSymbol] = useState("^GSPC");
  const [start, setStart] = useState("2024-01-01");
  const [end, setEnd] = useState("2024-12-31");
  const [eventDate, setEventDate] = useState("2024-03-11");
  const [eventCategory, setEventCategory] = useState("market_crash");
  const [scenarioName, setScenarioName] = useState("Broad market crash");
  const [assumedShock, setAssumedShock] = useState("-0.10");
  const [windows, setWindows] = useState("1,5,20");

  useEffect(() => {
    void api.getSentimentEvaluation()
      .then((response) => {
        setEvaluation(response.report);
        setEvaluationMessage(response.message);
        setEvaluationError(null);
      })
      .catch((requestError: unknown) => setEvaluationError(requestError instanceof Error ? requestError.message : "Evaluation status is unavailable"));
  }, []);

  async function runMarketResearch() {
    setRunning(true);
    setMarketError(null);
    try {
      const response = await api.getEventWindowResearch({
        symbol,
        start,
        end,
        event_date: eventDate,
        event_category: eventCategory,
        scenario_name: scenarioName,
        assumed_shock: Number(assumedShock),
        windows,
      });
      setMarket(response);
    } catch (requestError) {
      setMarketError(requestError instanceof Error ? requestError.message : "Market research is unavailable");
    } finally {
      setRunning(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Offline evaluation and historical research"
        title="Research"
        description="Measure the configured sentiment model and compare observed market-proxy returns with documented hypothetical stress assumptions. Research outputs are separate from live operations."
      />

      <section className="two-column-grid">
        <section className="section-block compact-section">
          <div className="section-kicker">Financial PhraseBank</div>
          <h2>Sentiment evaluation</h2>
          {evaluationError ? <ErrorState message={evaluationError} retry={() => window.location.reload()} /> : evaluation ? <EvaluationSummary report={evaluation} /> : <EmptyState title="Evaluation not available" description={evaluationMessage} />}
        </section>

        <section className="section-block compact-section">
          <div className="section-kicker">Historical market research</div>
          <h2>Compare an event window</h2>
          <p className="section-copy">This calls yfinance only when you submit the form. It does not change portfolio values or stress-test assumptions.</p>
          <div className="research-form">
            <label className="field-label">Ticker or index<input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="^GSPC" /></label>
            <label className="field-label">Start date<input type="date" value={start} onChange={(event) => setStart(event.target.value)} /></label>
            <label className="field-label">End date<input type="date" value={end} onChange={(event) => setEnd(event.target.value)} /></label>
            <label className="field-label">Event date<input type="date" value={eventDate} onChange={(event) => setEventDate(event.target.value)} /></label>
            <label className="field-label">Event category<input value={eventCategory} onChange={(event) => setEventCategory(event.target.value)} /></label>
            <label className="field-label">Scenario name<input value={scenarioName} onChange={(event) => setScenarioName(event.target.value)} /></label>
            <label className="field-label">Assumed shock<input inputMode="decimal" value={assumedShock} onChange={(event) => setAssumedShock(event.target.value)} /></label>
            <label className="field-label">Windows in trading days<input value={windows} onChange={(event) => setWindows(event.target.value)} /></label>
          </div>
          <button className="button button-primary" disabled={running} onClick={() => void runMarketResearch()} type="button">{running ? "Loading market data" : "Run event-window research"}</button>
          {marketError ? <p className="form-message">{marketError}</p> : null}
        </section>
      </section>

      {market ? <MarketResearchResult result={market} /> : null}
      <section className="section-block">
        <div className="section-kicker">Research boundaries</div>
        <p className="section-copy">PhraseBank is a sentence-level benchmark and yfinance provides an equity or index market proxy. Neither is a substitute for portfolio accounting, bond pricing, credit-model validation, or causal event studies.</p>
      </section>
    </>
  );
}

function EvaluationSummary({ report }: { report: SentimentEvaluationReport }) {
  return (
    <>
      <p className="section-copy">{report.dataset.name} / {report.dataset.configuration} · {report.metrics.evaluated_examples} examples · evaluated {formatDate(report.evaluation_date)}</p>
      <div className="metric-grid">
        <div className="metric-card"><span>Accuracy</span><strong>{formatPercent(report.metrics.accuracy * 100)}</strong></div>
        <div className="metric-card"><span>Macro-F1</span><strong>{formatPercent(report.metrics.macro_f1 * 100)}</strong></div>
      </div>
      <p className="section-copy">Model: <strong>{report.model.identifier}</strong> ({report.model.backend}). License: {report.dataset.license}.</p>
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead><tbody>{Object.entries(report.metrics.per_class).map(([label, values]) => <tr key={label}><td>{titleCase(label)}</td><td>{formatPercent(values.precision * 100)}</td><td>{formatPercent(values.recall * 100)}</td><td>{formatPercent(values.f1 * 100)}</td></tr>)}</tbody></table></div>
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Actual / predicted</th><th>Negative</th><th>Neutral</th><th>Positive</th></tr></thead><tbody>{Object.entries(report.metrics.confusion_matrix).map(([actual, row]) => <tr key={actual}><td>{titleCase(actual)}</td><td>{row.negative}</td><td>{row.neutral}</td><td>{row.positive}</td></tr>)}</tbody></table></div>
    </>
  );
}

function MarketResearchResult({ result }: { result: EventWindowResearchResponse }) {
  return (
    <section className="section-block">
      <div className="section-heading"><div><div className="section-kicker">Observed market research</div><h2>{result.series.symbol} event window</h2></div><span className="table-context">Retrieved {formatDate(result.series.retrieved_at)}</span></div>
      <p className="section-copy">Period: {result.series.start} to {result.series.end} · Price convention: {result.series.price_convention}. Event mapping preserves the original date and uses the same date or next available trading date.</p>
      <div className="table-wrap"><table className="data-table"><thead><tr><th>Window</th><th>Event date</th><th>Mapped date</th><th>Observed return</th><th>Assumed shock</th><th>Difference</th></tr></thead><tbody>{result.observations.map((observation) => <tr key={observation.window_trading_days}><td>{observation.window_trading_days} trading days</td><td>{observation.event_date}</td><td>{observation.mapped_trading_date} → {observation.observation_date}</td><td className={observation.observed_return < 0 ? "negative-value" : "positive-value"}>{formatPercent(observation.observed_return * 100)}</td><td>{formatPercent(observation.assumed_shock * 100)}</td><td>{formatPercent(observation.difference_observed_minus_assumed * 100)}</td></tr>)}</tbody></table></div>
      <div className="detail-copy"><div className="section-kicker">Limitations</div><ul className="method-list">{result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></div>
    </section>
  );
}
