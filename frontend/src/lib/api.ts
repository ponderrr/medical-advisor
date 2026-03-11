import type {
  Conflict,
  DosingProtocol,
  HealthResponse,
  Mechanism,
  MetaResponse,
  QueryRequest,
  QueryResponse,
  SideEffect,
  StatsResponse,
  SynthesisSummary,
} from "@/types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function GET<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(k, String(v));
    });
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, text);
  }
  return res.json() as Promise<T>;
}

async function POST<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, text);
  }
  return res.json() as Promise<T>;
}

export { ApiError };

export const api = {
  health: () => GET<HealthResponse>("/api/health"),
  meta: () => GET<MetaResponse>("/api/meta"),
  stats: () => GET<StatsResponse>("/api/stats"),
  summary: () => GET<SynthesisSummary>("/api/synthesis/summary"),

  dosing: (params?: { source_type?: string; min_confidence?: number; limit?: number }) =>
    GET<DosingProtocol[]>("/api/synthesis/dosing", params),

  sideEffects: (params?: { severity?: string; min_frequency?: number; limit?: number }) =>
    GET<SideEffect[]>("/api/synthesis/side-effects", params),

  mechanisms: (params?: { receptor?: string; limit?: number }) =>
    GET<Mechanism[]>("/api/synthesis/mechanisms", params),

  conflicts: (params?: { conflict_type?: string; limit?: number }) =>
    GET<Conflict[]>("/api/synthesis/conflicts", params),

  query: (body: QueryRequest) => POST<QueryResponse>("/api/query", body),
};
