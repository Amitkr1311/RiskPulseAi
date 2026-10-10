"use client";

import { useEffect, useState } from "react";

type HealthStatus = {
  status: "healthy" | "degraded";
  service: string;
  version: string;
  database: { status: "healthy" | "unavailable" };
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadHealth = async () => {
      try {
        const response = await fetch(`${apiUrl}/health`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Backend returned HTTP ${response.status}`);
        }
        setHealth((await response.json()) as HealthStatus);
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Backend unavailable");
      }
    };

    void loadHealth();
  }, []);

  const status = error ? "degraded" : health?.status ?? "pending";
  const label = status === "pending" ? "Checking" : status === "healthy" ? "Healthy" : "Unavailable";

  return (
    <main className="page">
      <div className="eyebrow">RiskPulse AI · Milestone 1</div>
      <h1>Financial risk intelligence, starting with a reliable foundation.</h1>
      <p className="lede">
        This minimal status page confirms that the frontend can reach the FastAPI service and that the
        service can reach its database.
      </p>

      <section className="status-card" aria-live="polite">
        <div className="status-heading">
          <h2>Environment status</h2>
          <span className={`status-pill ${status}`}>{label}</span>
        </div>
        <div className="status-details">
          {health ? (
            <>
              <div>
                API service: <strong>{health.service}</strong>
              </div>
              <div>
                API version: <strong>{health.version}</strong>
              </div>
              <div>
                PostgreSQL dependency: <strong>{health.database.status}</strong>
              </div>
            </>
          ) : (
            <div>{error ?? "Contacting the backend…"}</div>
          )}
        </div>
      </section>

      <p className="note">
        Demo fixtures are deterministic and clearly separate from live provider data. Ingestion, NLP, and
        stress-testing calculations arrive in later milestones.
      </p>
    </main>
  );
}

