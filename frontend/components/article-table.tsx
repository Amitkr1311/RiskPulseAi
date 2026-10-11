import type { Article, RiskSignal } from "@/lib/api";
import { cleanText, formatDate, formatRelative, titleCase } from "@/lib/format";
import { ImpactMark, SourceMark } from "@/components/ui";

export function ArticleTable({ articles, signalsByArticle }: { articles: Article[]; signalsByArticle?: Map<number, RiskSignal> }) {
  return (
    <div className="table-wrap">
      <table className="data-table article-table">
        <thead>
          <tr>
            <th>Headline</th>
            <th>Source</th>
            <th>Published</th>
            <th>Ingested</th>
            <th>Processing</th>
            <th>Risk</th>
          </tr>
        </thead>
        <tbody>
          {articles.map((article) => {
            const signal = signalsByArticle?.get(article.id);
            return (
              <tr key={article.id}>
                <td className="headline-cell">
                  {article.url ? <a href={article.url} rel="noreferrer" target="_blank">{cleanText(article.title)}</a> : <strong>{cleanText(article.title)}</strong>}
                  <span className="cell-subtext">{article.is_demo ? "Demo fixture" : article.is_historical ? "Historical replay · " : ""}{!article.is_demo ? `${cleanText(article.text).slice(0, 140)}${cleanText(article.text).length > 140 ? "…" : ""}` : ""}</span>
                </td>
                <td><SourceMark source={article.source} />{article.is_historical ? <span className="cell-subtext">Historical</span> : null}</td>
                <td className="tabular nowrap">{formatDate(article.published_at)}</td>
                <td className="tabular nowrap">{formatRelative(article.ingested_at)}<span className="cell-subtext">{formatDate(article.ingested_at)}</span></td>
                <td><span className="text-label">{titleCase(article.processing_status)}</span></td>
                <td>{signal ? <ImpactMark score={signal.impact_score} /> : <span className="muted">Not available</span>}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {!articles.length ? <div className="table-empty">No articles match the current filters.</div> : null}
    </div>
  );
}
