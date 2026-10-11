"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { api, type DashboardSummary } from "@/lib/api";
import { formatDate, formatRelative } from "@/lib/format";

const navigation = [
  { href: "/", label: "Overview", mark: "O" },
  { href: "/signals", label: "Risk Signals", mark: "S" },
  { href: "/news", label: "News Feed", mark: "N" },
  { href: "/portfolio", label: "Portfolio", mark: "P" },
  { href: "/stress-testing", label: "Stress Testing", mark: "T" },
  { href: "/research", label: "Research", mark: "R" },
];

const titles: Record<string, string> = {
  "/": "Overview",
  "/signals": "Risk Signals",
  "/news": "News Feed",
  "/portfolio": "Portfolio",
  "/stress-testing": "Stress Testing",
  "/research": "Research",
};

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const loadShell = async () => {
    try {
      const dashboard = await api.getDashboardSummary();
      setSummary(dashboard);
    } catch { /* Keep the last known freshness values without exposing infrastructure state. */ }
  };

  useEffect(() => {
    void loadShell();
    const timer = window.setInterval(() => void loadShell(), 15_000);
    return () => window.clearInterval(timer);
  }, []);

  const lastFetch = summary?.latest_ingestion_at;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="wordmark" href="/">
          <span className="wordmark-mark" aria-hidden="true"><span /><span /><span /></span>
          <span>RiskPulse <em>AI</em></span>
        </Link>
        <div className="sidebar-rule" />
        <nav aria-label="Primary navigation" className="main-nav">
          <div className="nav-label">Workspace</div>
          {navigation.map((item) => {
            const active = pathname === item.href;
            return (
              <Link className={`nav-link ${active ? "active" : ""}`} href={item.href} key={item.href}>
                <span className="nav-mark" aria-hidden="true">{item.mark}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <div className="nav-label">Coverage</div>
          <div className="sidebar-source">RSS · REDDIT</div>
          <div className="sidebar-note">Financial source records and risk signals are refreshed periodically.</div>
        </div>
      </aside>
      <div className="content-column">
        <header className="topbar">
          <div className="breadcrumbs"><span>RiskPulse AI</span><span>/</span><strong>{titles[pathname] ?? "Workspace"}</strong></div>
          <div className="topbar-meta">
            <span>Last fetch <strong className="tabular">{lastFetch ? formatRelative(lastFetch) : "Not available"}</strong></span>
            <span className="topbar-divider" aria-hidden="true" />
            <span>{formatDate(lastFetch)}</span>
          </div>
        </header>
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}
