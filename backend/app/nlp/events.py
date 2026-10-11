import re

from app.nlp.contracts import EventResult

EVENT_TYPES = (
    "geopolitical",
    "macroeconomic",
    "credit_event",
    "merger_acquisition",
    "earnings",
    "regulatory",
    "product_launch",
    "market_crash",
    "company_performance",
    "liquidity_stress",
    "cyber_incident",
    "fraud_misconduct",
    "litigation",
    "operational_disruption",
    "climate_risk",
    "sovereign_risk",
    "currency_shock",
    "other",
)

EVENT_GROUPS: dict[str, tuple[str, ...]] = {
    "market_macro": ("geopolitical", "macroeconomic", "market_crash", "sovereign_risk", "currency_shock"),
    "credit_financial": ("credit_event", "earnings", "company_performance", "liquidity_stress"),
    "corporate_actions": ("merger_acquisition", "product_launch"),
    "regulatory_legal": ("regulatory", "fraud_misconduct", "litigation"),
    "operational_technology": ("operational_disruption", "cyber_incident"),
    "climate_esg": ("climate_risk",),
    "other": ("other",),
}

ENTITY_TYPES = (
    "organization",
    "central_bank",
    "government",
    "country",
    "sector",
    "commodity",
    "currency",
    "index",
    "instrument",
    "person",
)

EVENT_PATTERNS: dict[str, tuple[str, ...]] = {
    "geopolitical": (
        "geopolitical",
        "sanctions",
        "sanction",
        "conflict",
        "war",
        "tariff",
        "embargo",
        "supply-chain disruption",
        "trade restriction",
    ),
    "macroeconomic": ("central bank", "interest rate", "inflation", "recession", "monetary policy", "unemployment", "gdp growth"),
    "credit_event": ("default", "missed payment", "debt restructuring", "credit downgrade", "bankruptcy", "non-performing loan", "rating downgrade"),
    "merger_acquisition": ("merger", "acquisition", "acquires", "takeover", "buyout"),
    "earnings": ("earnings", "quarterly results", "financial results", "guidance"),
    "regulatory": ("regulator", "regulatory", "fine", "compliance", "new rule", "investigation", "sanctioned by regulator"),
    "product_launch": ("product launch", "new product", "launches", "unveiled"),
    "market_crash": ("market crash", "market collapse", "sell-off", "plunge", "crash", "bear market"),
    "company_performance": ("revenue", "profit", "operating income", "sales growth", "performance"),
    "liquidity_stress": ("liquidity", "cash crunch", "margin call", "deposit outflow", "redemptions", "funding stress"),
    "cyber_incident": ("cyberattack", "cyber attack", "ransomware", "data breach", "hacked", "security incident"),
    "fraud_misconduct": ("fraud", "misconduct", "embezzlement", "accounting irregularity", "money laundering"),
    "litigation": ("lawsuit", "litigation", "court ruling", "legal claim", "class action", "legal dispute"),
    "operational_disruption": ("operational disruption", "system outage", "service outage", "plant shutdown", "production halt", "supply disruption"),
    "climate_risk": ("climate risk", "flood", "wildfire", "extreme weather", "drought", "carbon regulation"),
    "sovereign_risk": ("sovereign default", "government debt", "political instability", "debt-to-gdp", "sovereign downgrade"),
    "currency_shock": ("currency depreciation", "currency devaluation", "forex volatility", "exchange rate shock", "rupee weakens", "dollar strengthens"),
}


def event_group_for_type(event_type: str) -> str:
    normalized = event_type.casefold()
    return next((group for group, event_types in EVENT_GROUPS.items() if normalized in event_types), "other")


def event_types_for_group(event_group: str) -> tuple[str, ...]:
    return EVENT_GROUPS.get(event_group.casefold(), ())


class RuleBasedEventClassifier:
    def classify(self, text: str) -> EventResult:
        normalized = text.casefold()
        candidates: list[tuple[int, str, tuple[str, ...]]] = []
        for event_type, patterns in EVENT_PATTERNS.items():
            matched = tuple(term for term in patterns if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", normalized))
            if matched:
                candidates.append((len(matched), event_type, matched))
        if not candidates:
            return EventResult("other", 0.15, (), "rules-v2")
        count, event_type, matched = max(candidates, key=lambda item: (item[0], item[1]))
        confidence = min(0.99, 0.35 + count * 0.15)
        return EventResult(event_type, confidence, matched, "rules-v2")
