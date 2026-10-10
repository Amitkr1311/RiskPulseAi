import type { ReactNode } from "react";

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow ? <div className="eyebrow">{eyebrow}</div> : null}
        <h1>{title}</h1>
        {description ? <p className="page-description">{description}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </div>
  );
}

export function LoadingState({ label = "Loading data" }: { label?: string }) {
  return <div className="state-panel"><span className="loading-mark" aria-hidden="true" />{label}</div>;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="state-panel empty-state">
      <div className="state-kicker">No data</div>
      <h2>{title}</h2>
      <p>{description}</p>
      {action ? <div className="state-action">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="state-panel error-state" role="alert">
      <div className="state-kicker">Request unavailable</div>
      <h2>Data could not be loaded</h2>
      <p>{message}</p>
      {retry ? <button className="button button-secondary" onClick={retry} type="button">Retry</button> : null}
    </div>
  );
}

export function Metric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value tabular">{value}</div>
      {detail ? <div className="metric-detail">{detail}</div> : null}
    </div>
  );
}

export function ImpactMark({ score }: { score: number }) {
  const label = score >= 8 ? "CRITICAL" : score >= 6 ? "HIGH" : score >= 4 ? "MEDIUM" : "LOW";
  return <span className="impact-mark"><span className="impact-blocks" aria-hidden="true">{"■".repeat(Math.min(score, 10))}</span> {label} <strong>{score}/10</strong></span>;
}

export function SourceMark({ source }: { source: string }) {
  return <span className="source-mark"><span className="source-dot" aria-hidden="true" />{source === "reddit" ? "Reddit" : source === "news" ? "RSS" : source}</span>;
}

