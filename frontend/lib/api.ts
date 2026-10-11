export type HealthStatus = {
  status: "healthy" | "degraded";
  service: string;
  version: string;
  database: { status: "healthy" | "unavailable" };
};

export type Article = {
  id: number;
  source: string;
  external_id: string | null;
  title: string;
  text: string;
  url: string | null;
  published_at: string | null;
  ingested_at: string;
  content_hash: string;
  is_demo: boolean;
  is_historical: boolean;
  source_metadata: Record<string, unknown> | null;
  processing_status: string;
  processing_error: string | null;
  processing_attempts: number;
  processed_at: string | null;
};

export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type EntitySignal = {
  mention: string;
  canonical_name: string;
  identifier: string | null;
  resolved: boolean;
  entity_type: string;
};

export type RiskSignal = {
  id: number;
  article_id: number;
  source: string;
  article_title: string;
  article_url: string | null;
  is_demo: boolean;
  article: Article;
  entities: EntitySignal[];
  sentiment_label: string | null;
  sentiment_score: number;
  sentiment_probabilities: Record<string, number> | null;
  event_type: string;
  event_group: string;
  event_confidence: number | null;
  impact_score: number;
  impact_factors: Record<string, unknown> | null;
  explanation: string;
  model_version: string;
  model_metadata: Record<string, unknown> | null;
  scoring_config_version: string;
  created_at: string;
};

export type DashboardSummary = {
  total_articles: number;
  processed_articles: number;
  pending_articles: number;
  failed_articles: number;
  total_signals: number;
  high_impact_signals: number;
  high_impact_threshold: number;
  recent_signal_counts: { last_24_hours: number; last_7_days: number; last_30_days: number };
  live_articles: number;
  demo_articles: number;
  latest_ingestion_at: string | null;
  latest_processed_at: string | null;
};

export type SignalTaxonomy = {
  event_groups: Record<string, string[]>;
  event_types: string[];
  entity_types: string[];
};

export type SentimentEvaluationReport = {
  schema_version: string;
  dataset: { name: string; configuration: string; source: string; license: string };
  model: { backend: string; identifier: string; label_mapping: Record<string, string>; score_definition: string; runtime_marker: string };
  evaluation_date: string;
  seed: number;
  metrics: {
    accuracy: number;
    macro_f1: number;
    evaluated_examples: number;
    class_distribution: Record<string, number>;
    per_class: Record<string, { precision: number; recall: number; f1: number }>;
    confusion_matrix: Record<string, Record<string, number>>;
  };
  limitations: string[];
};

export type SentimentEvaluationResponse = {
  available: boolean;
  report: SentimentEvaluationReport | null;
  message: string;
};

export type MarketResearchResponse = {
  symbol: string;
  start: string;
  end: string;
  retrieved_at: string;
  price_convention: string;
  prices: { trading_date: string; close: number }[];
};

export type EventWindowResearchResponse = {
  series: MarketResearchResponse;
  observations: {
    symbol: string;
    event_timestamp: string;
    event_date: string;
    mapped_trading_date: string;
    mapping_policy: string;
    event_category: string;
    scenario_name: string;
    assumed_shock: number;
    window_trading_days: number;
    observation_date: string;
    observed_return: number;
    difference_observed_minus_assumed: number;
  }[];
  limitations: string[];
};

export type SourceStatus = {
  source: string;
  enabled: boolean;
  configured: boolean;
  last_run: {
    run_id: number;
    source: string;
    status: string;
    records_seen: number;
    records_created: number;
    duplicates_skipped: number;
    records_failed: number;
    error_category: string | null;
    started_at: string;
    completed_at: string | null;
  } | null;
};

export type IngestionStatus = {
  sources: SourceStatus[];
  recent_runs: SourceStatus["last_run"][];
  live_enabled: boolean;
  poll_interval_seconds: number;
};

export type NlpStatus = {
  sentiment_backend: string;
  sentiment_model_id: string;
  model_available: boolean;
  model_download_allowed: boolean;
  pending_articles: number;
  failed_articles: number;
  processed_articles: number;
  signal_count: number;
};

export type PortfolioAllocation = {
  asset_class: string;
  market_value_inr: string;
  market_value_crore: string;
  allocation_percentage: string;
};

export type SectorAllocation = {
  sector: string;
  market_value_inr: string;
  allocation_percentage: string;
};

export type PortfolioSummary = {
  portfolio_id: number;
  portfolio_key: string;
  name: string;
  currency: string;
  total_market_value_inr: string;
  total_market_value_crore: string;
  position_count: number;
  asset_class_allocations: PortfolioAllocation[];
  sector_allocations: SectorAllocation[];
  is_demo: boolean;
};

export type Portfolio = PortfolioSummary & {
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type PortfolioPosition = {
  id: number;
  portfolio_id: number;
  portfolio_key: string;
  position_key: string;
  name: string;
  asset_class: string;
  currency: string;
  market_value_inr: string;
  market_value_crore: string;
  contribution_percentage: string;
  sector: string | null;
  borrower: string | null;
  valuation_parameters: Record<string, unknown>;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
};

export type StressScenario = {
  scenario_id: string;
  database_id: number;
  name: string;
  description: string;
  event_category: string;
  supported_event_types: string[];
  required_signal_fields: string[];
  relevance_scope: string;
  trigger_threshold: number;
  version: string;
  enabled: boolean;
  assumptions: string;
  parameters: { name: string; value: string; unit: string; interpretation: string }[];
};

export type StressRunSummary = {
  simulation_id: number;
  run_id: number;
  portfolio_id: number | null;
  scenario_id: string;
  scenario_name: string;
  scenario_version: string;
  trigger_signal_id: number | null;
  trigger_mode: string;
  status: string;
  portfolio_value_before: string;
  portfolio_value_after: string;
  pnl: string;
  loss_percentage: string;
  portfolio_return_percentage: string;
  created_at: string;
};

export type StressRunDetail = StressRunSummary & {
  model_version: string;
  scenario_parameters: Record<string, unknown>;
  input_snapshot: Record<string, unknown>;
  data_provenance: Record<string, unknown>;
  validation_warnings: string[];
  reconciliation: { position_pnl_sum: string; reported_pnl: string; difference: string; tolerance: string; reconciled: boolean };
  trigger_signal: RiskSignal | null;
  results: {
    result_id: number;
    position_id: number;
    position_key: string | null;
    position_name: string | null;
    asset_type: string | null;
    position_value_before: string;
    position_value_after: string;
    contribution: string;
    inclusion_status: string;
    calculation_method: string | null;
    explanation: string | null;
    applied_shocks: Record<string, unknown>;
    calculation_details: Record<string, unknown>;
  }[];
};

export type StressEligibility = {
  signal_id: number;
  eligible: boolean;
  impact_score: number;
  impact_threshold: number;
  matching_scenarios: string[];
  reasons: string[];
  relevance_assessment: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    let detail = `Request failed with HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Keep the useful HTTP status when the backend does not return JSON.
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

function query(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  getHealth: () => request<HealthStatus>("/health"),
  getDashboardSummary: () => request<DashboardSummary>("/dashboard/summary"),
  getIngestionStatus: () => request<IngestionStatus>("/ingestion/status"),
  getNlpStatus: () => request<NlpStatus>("/nlp/status"),
  getArticles: (params: Record<string, string | number | undefined> = {}) =>
    request<Page<Article>>(`/articles${query(params)}`),
  getSignals: (params: Record<string, string | number | boolean | undefined> = {}) =>
    request<Page<RiskSignal>>(`/signals${query(params)}`),
  getSignalTaxonomy: () => request<SignalTaxonomy>("/signals/taxonomy"),
  getSentimentEvaluation: () => request<SentimentEvaluationResponse>("/research/sentiment-evaluation"),
  getMarketResearch: (params: Record<string, string | number | undefined>) =>
    request<MarketResearchResponse>(`/research/market-data${query(params)}`),
  getEventWindowResearch: (params: Record<string, string | number | undefined>) =>
    request<EventWindowResearchResponse>(`/research/event-window${query(params)}`),
  getSignal: (id: number) => request<RiskSignal>(`/signals/${id}`),
  getPortfolio: () => request<Portfolio>("/portfolio"),
  getPortfolioSummary: () => request<PortfolioSummary>("/portfolio/summary"),
  getPortfolioPositions: (params: Record<string, string | number | undefined> = {}) =>
    request<Page<PortfolioPosition>>(`/portfolio/positions${query(params)}`),
  getStressScenarios: () => request<StressScenario[]>('/stress-testing/scenarios'),
  getStressRuns: (params: Record<string, string | number | undefined> = {}) =>
    request<Page<StressRunSummary>>(`/stress-testing/runs${query(params)}`),
  getStressRun: (id: number) => request<StressRunDetail>(`/stress-testing/runs/${id}`),
  runStressTest: (body: { portfolio_id?: number; scenario_id: string; risk_signal_id?: number; trigger_mode?: string; fresh_run?: boolean }) =>
    request<StressRunDetail>('/stress-testing/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  getStressEligibility: (signalId: number, portfolioId?: number) =>
    request<StressEligibility>(`/stress-testing/signals/${signalId}/eligibility${query({ portfolio_id: portfolioId })}`),
};
