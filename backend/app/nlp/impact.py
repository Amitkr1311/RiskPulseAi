from app.nlp.contracts import EventResult, ImpactResult, SentimentResult

SEVERITY = {
    "geopolitical": 0.85,
    "macroeconomic": 0.70,
    "credit_event": 1.00,
    "merger_acquisition": 0.55,
    "earnings": 0.50,
    "regulatory": 0.65,
    "product_launch": 0.35,
    "market_crash": 1.00,
    "company_performance": 0.50,
    "other": 0.15,
}
SOURCE_RELIABILITY = {"news": 0.80, "reddit": 0.45, "demo": 0.60}


class ImpactScorer:
    version = "impact-v1"

    def score(self, source: str, event: EventResult, sentiment: SentimentResult) -> ImpactResult:
        severity = SEVERITY.get(event.event_type, SEVERITY["other"])
        sentiment_magnitude = min(1.0, abs(sentiment.score))
        reliability = SOURCE_RELIABILITY.get(source.casefold(), 0.40)
        weighted = 0.65 * severity + 0.20 * sentiment_magnitude + 0.15 * reliability
        score = max(1, min(10, int(round(1 + 9 * weighted))))
        factors: dict[str, float | str] = {
            "severity": severity,
            "sentiment_magnitude": sentiment_magnitude,
            "source_reliability": reliability,
            "severity_weight": 0.65,
            "sentiment_weight": 0.20,
            "source_weight": 0.15,
            "weighted_total": weighted,
            "formula_version": self.version,
            "portfolio_relevance": "not_assessed_in_milestone_3",
        }
        rationale = (
            f"Heuristic impact {score}/10 from {event.event_type} severity {severity:.2f}, "
            f"sentiment magnitude {sentiment_magnitude:.2f}, and {source} reliability {reliability:.2f}. "
            "Portfolio relevance is not assessed in Milestone 3."
        )
        return ImpactResult(score, factors, rationale)
