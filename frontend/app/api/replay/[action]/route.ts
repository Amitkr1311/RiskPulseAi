import fs from "node:fs";
import path from "node:path";

import { NextRequest } from "next/server";

const allowedActions = new Set(["start", "pause", "resume", "stop", "reset"]);

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ action: string }> },
) {
  const { action } = await context.params;
  if (!allowedActions.has(action)) {
    return Response.json({ detail: "Unknown replay action" }, { status: 404 });
  }

  const backendUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const headers = new Headers({ "Content-Type": "application/json" });
  const ingestionKey = serverOnlyIngestionKey();
  if (ingestionKey) headers.set("X-Ingestion-Key", ingestionKey);

  const upstream = await fetch(`${backendUrl}/replay/${action}`, {
    method: "POST",
    headers,
    body: action === "start" ? await request.text() : undefined,
    cache: "no-store",
  });
  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
  });
}

function serverOnlyIngestionKey(): string | undefined {
  if (process.env.INGESTION_API_KEY !== undefined) return process.env.INGESTION_API_KEY;

  // Next.js loads frontend/.env.local, while this project keeps the shared
  // development settings in the repository-root .env. Read that fallback only
  // on the server; it is never included in a browser response or bundle.
  try {
    const rootEnv = fs.readFileSync(path.resolve(process.cwd(), "..", ".env"), "utf8");
    const line = rootEnv.split(/\r?\n/).find((candidate) => candidate.startsWith("INGESTION_API_KEY="));
    return line?.slice("INGESTION_API_KEY=".length).trim().replace(/^['"]|['"]$/g, "");
  } catch {
    return undefined;
  }
}
