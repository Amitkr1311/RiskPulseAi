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
    "liquidity_stress": 0.90,
    "cyber_incident": 0.80,
    "fraud_misconduct": 0.80,
    "litigation": 0.60,
    "operational_disruption": 0.70,
    "climate_risk": 0.70,
    "sovereign_risk": 0.85,
    "currency_shock": 0.75,
    "other": 0.15,
}
SOURCE_RELIABILITY = {"news": 0.80, "social": 0.50, "reddit": 0.45, "demo": 0.60}


class ImpactScorer:
    version = "impact-v3"

    def score(
        self,
        source: str,
        event: EventResult,
        sentiment: SentimentResult,
        entity_exposure: int | float = 0,
    ) -> ImpactResult:
        event_type_weight = SEVERITY.get(event.event_type, SEVERITY["other"])
        sentiment_magnitude = min(1.0, abs(sentiment.score))
        reliability = SOURCE_RELIABILITY.get(source.casefold(), 0.40)
        normalized_entity_exposure = min(1.0, max(0.0, float(entity_exposure)))
        weighted = (
            0.60 * event_type_weight
            + 0.20 * sentiment_magnitude
            + 0.10 * reliability
            + 0.10 * normalized_entity_exposure
        )
        score = max(1, min(10, int(round(1 + 9 * weighted))))
        factors: dict[str, float | str] = {
            "event_type_weight": event_type_weight,
            "severity": event_type_weight,
            "sentiment_magnitude": sentiment_magnitude,
            "entity_exposure": normalized_entity_exposure,
            "entity_exposure_count": float(entity_exposure),
            "source_reliability": reliability,
            "event_type_weight_weight": 0.60,
            "sentiment_weight": 0.20,
            "source_weight": 0.10,
            "entity_exposure_weight": 0.10,
            "weighted_total": weighted,
            "formula_version": self.version,
        }
        rationale = (
            f"Impact {score}/10 from sentiment magnitude {sentiment_magnitude:.2f}, "
            f"event-type weight {event_type_weight:.2f}, entity exposure {normalized_entity_exposure:.2f}, "
            f"and {source} reliability {reliability:.2f}."
        )
        return ImpactResult(score, factors, rationale)
