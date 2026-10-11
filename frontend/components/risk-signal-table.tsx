import Link from "next/link";

import type { RiskSignal } from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";
import { ImpactMark, SourceMark } from "@/components/ui";

export function RiskSignalTable({ signals, onSelect }: { signals: RiskSignal[]; onSelect?: (signal: RiskSignal) => void }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Impact</th>
            <th>Entity</th>
            <th>Event type</th>
            <th>Sentiment</th>
            <th>Source</th>
            <th>Detected</th>
            <th>Rationale</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => {
            const entity = signal.entities[0]?.canonical_name ?? "Unresolved";
            return (
              <tr className="interactive-row" key={signal.id} onClick={() => onSelect?.(signal)}>
                <td><ImpactMark score={signal.impact_score} /></td>
                <td><strong>{entity}</strong><span className="cell-subtext">{signal.entities.length} mention{signal.entities.length === 1 ? "" : "s"}</span></td>
                <td>{titleCase(signal.event_type)}</td>
                <td><span className="text-label">{signal.sentiment_label ?? "Not available"}</span><span className="cell-subtext tabular">{signal.sentiment_score.toFixed(2)}</span></td>
                <td><SourceMark source={signal.source} />{signal.article.is_historical ? <span className="cell-subtext">Historical replay</span> : null}</td>
                <td className="tabular nowrap">{formatDate(signal.created_at)}</td>
                <td className="rationale-cell">{signal.explanation}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {!signals.length ? <div className="table-empty">No signals match the current filters.</div> : null}
    </div>
  );
}

export function SignalArticleLink({ signal }: { signal: RiskSignal }) {
  return signal.article_url ? <Link className="inline-link" href={signal.article_url} rel="noreferrer" target="_blank">Open source article</Link> : <span>Source URL unavailable</span>;
}
