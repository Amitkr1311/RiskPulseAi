"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ErrorState, EmptyState, LoadingState, PageHeader } from "@/components/ui";
import { api, type RiskSignal, type StressRunDetail, type StressRunSummary, type StressScenario } from "@/lib/api";
import { formatDate, formatInr, formatPercent, titleCase } from "@/lib/format";

export default function StressTestingPage() {
  const [scenarios, setScenarios] = useState<StressScenario[]>([]);
  const [signals, setSignals] = useState<RiskSignal[]>([]);
  const [runs, setRuns] = useState<StressRunSummary[]>([]);
  const [detail, setDetail] = useState<StressRunDetail | null>(null);
  const [scenarioId, setScenarioId] = useState("");
  const [signalId, setSignalId] = useState("");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const detailRef = useRef<HTMLElement | null>(null);

  const selectedScenario = useMemo(
    () => scenarios.find((scenario) => scenario.scenario_id === scenarioId) ?? null,
    [scenarioId, scenarios],
  );

  async function load() {
    setLoading(true);
    try {
      const [scenarioData, signalData, runData] = await Promise.all([
        api.getStressScenarios(),
        api.getSignals({ limit: 50, impact_min: 8 }),
        api.getStressRuns({ limit: 20 }),
      ]);
      setScenarios(scenarioData);
      setSignals(signalData.items);
      setRuns(runData.items);
      setScenarioId((current) => current || scenarioData[0]?.scenario_id || "");
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Stress-testing data is unavailable");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (detail) detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [detail]);

  async function runSimulation() {
    if (!scenarioId) return;
    setRunning(true);
    setRunMessage(null);
    try {
      const result = await api.runStressTest({
        scenario_id: scenarioId,
        risk_signal_id: signalId ? Number(signalId) : undefined,
        trigger_mode: "manual",
      });
      setDetail(result);
      setRunMessage("Simulation completed and persisted.");
      const history = await api.getStressRuns({ limit: 20 });
      setRuns(history.items);
    } catch (requestError) {
      setRunMessage(requestError instanceof Error ? requestError.message : "Simulation could not be run");
    } finally {
      setRunning(false);
    }
  }

  if (loading) return <LoadingState label="Loading stress-testing workspace" />;
  if (error) return <ErrorState message={error} retry={() => void load()} />;

  return (
    <>
      <PageHeader
        eyebrow="Hypothetical analysis"
        title="Stress Testing"
        description="Run deterministic, auditable scenario analyses against the persisted synthetic portfolio. Results are hypothetical and not forecasts."
        actions={<button className="button button-secondary" onClick={() => void load()} type="button">Refresh</button>}
      />

      <section className="two-column-grid">
        <section className="section-block compact-section">
          <div className="section-kicker">Simulation controls</div>
          <h2>Run a scenario</h2>
          <label className="field-label">Scenario
            <select onChange={(event) => setScenarioId(event.target.value)} value={scenarioId}>
              {scenarios.map((scenario) => <option key={scenario.scenario_id} value={scenario.scenario_id}>{scenario.name}</option>)}
            </select>
          </label>
          <label className="field-label">Triggering high-impact signal (optional for broad scenarios)
            <select onChange={(event) => setSignalId(event.target.value)} value={signalId}>
              <option value="">Manual scenario run</option>
              {signals.map((signal) => <option key={signal.id} value={signal.id}>#{signal.id} / {titleCase(signal.event_type)} / impact {signal.impact_score}</option>)}
            </select>
          </label>
          {selectedScenario && <p className="section-copy">Scope: <strong>{titleCase(selectedScenario.relevance_scope)}</strong>. Threshold: impact &gt; {selectedScenario.trigger_threshold}. Targeted scenarios require a matching signal entity or sector.</p>}
          <button className="button button-primary" disabled={!scenarioId || running} onClick={() => void runSimulation()} type="button">{running ? "Running simulationâ€¦" : "Run simulation"}</button>
          {runMessage && <p className="form-message">{runMessage}</p>}
        </section>

        <section className="section-block compact-section">
          <div className="section-kicker">Scenario assumptions</div>
          {selectedScenario ? <><h2>{selectedScenario.name}</h2><p className="section-copy">{selectedScenario.assumptions}</p><div className="assumption-list">{selectedScenario.parameters.map((parameter) => <div className="assumption-row" key={parameter.name}><span>{parameter.interpretation}</span><strong>{parameter.value} {titleCase(parameter.unit)}</strong></div>)}</div></> : <EmptyState title="No scenarios available" description="Seed the scenario definitions before running a simulation." />}
        </section>
      </section>

      {detail && <section className="section-block" id="stress-result" ref={detailRef}>
        <div className="section-heading"><div><div className="section-kicker">Selected simulation result</div><h2>{detail.scenario_name}</h2></div><span className={"status-label " + (detail.status === "completed" ? "positive" : "muted")}>{titleCase(detail.status)}</span></div>
        <div className="metric-grid">
          <div className="metric-card"><span>Base value</span><strong>{formatInr(detail.portfolio_value_before)}</strong></div>
          <div className="metric-card"><span>Stressed value</span><strong>{formatInr(detail.portfolio_value_after)}</strong></div>
          <div className="metric-card"><span>P&amp;L</span><strong>{formatInr(detail.pnl)}</strong></div>
          <div className="metric-card"><span>Loss percentage</span><strong>{formatPercent(detail.loss_percentage)}</strong></div>
        </div>
        <p className="section-copy">Reconciliation: {detail.reconciliation.reconciled ? "passed" : "failed"} / position P&amp;L sum {formatInr(detail.reconciliation.position_pnl_sum)} / difference {formatInr(detail.reconciliation.difference)}</p>
        {detail.trigger_signal && <p className="section-copy">Trigger: #{detail.trigger_signal.id} / {titleCase(detail.trigger_signal.event_type)} / {detail.trigger_signal.article_title}</p>}
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Position</th><th>Asset class</th><th>Status</th><th>Base value</th><th>Stressed value</th><th>Contribution</th></tr></thead><tbody>{detail.results.map((result) => <tr key={result.result_id}><td><strong>{result.position_name ?? result.position_key}</strong><span className="cell-subtext">{result.explanation}</span></td><td>{titleCase(result.asset_type ?? "")}</td><td>{titleCase(result.inclusion_status)}</td><td>{formatInr(result.position_value_before)}</td><td>{formatInr(result.position_value_after)}</td><td className={Number(result.contribution) < 0 ? "negative-value" : "positive-value"}>{formatInr(result.contribution)}</td></tr>)}</tbody></table></div>
      </section>}

      <section className="section-block">
        <div className="section-heading"><div><div className="section-kicker">Simulation history</div><h2>{runs.length} persisted run{runs.length === 1 ? "" : "s"}</h2></div></div>
        {runs.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Scenario</th><th>Mode</th><th>Status</th><th>P&amp;L</th><th>Created</th><th /></tr></thead><tbody>{runs.map((run) => <tr key={run.simulation_id}><td>{run.scenario_name}<span className="cell-subtext">Version {run.scenario_version}</span></td><td>{titleCase(run.trigger_mode)}</td><td>{titleCase(run.status)}</td><td className={Number(run.pnl) < 0 ? "negative-value" : "positive-value"}>{formatInr(run.pnl)}</td><td>{formatDate(run.created_at)}</td><td><button className="button button-quiet" onClick={() => api.getStressRun(run.simulation_id).then(setDetail).catch((requestError: unknown) => setRunMessage(requestError instanceof Error ? requestError.message : "Run detail unavailable"))} type="button">Inspect</button></td></tr>)}</tbody></table></div> : <EmptyState title="No simulations yet" description="Run a broad-market scenario or select a qualifying risk signal to create the first persisted result." />}
      </section>
    </>
  );
}

