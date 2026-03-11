"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DosingProtocol } from "@/types/api";
import { DosingDistributionChart } from "@/components/charts/DosingDistributionChart";
import { LoadingGrid } from "@/components/ui/LoadingCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { FlaskConical } from "lucide-react";

const SOURCE_TYPES = ["all", "paper", "trial", "reddit", "twitter"];

function ConfidenceBar({ value }: { value: string | null }) {
  const map: Record<string, number> = { low: 25, medium: 60, high: 90 };
  const pct = value ? (map[value.toLowerCase()] ?? 50) : 0;
  const color = pct >= 80 ? "#22c55e" : pct >= 50 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--border)" }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[10px] text-[#6b7280] w-10 text-right">{value ?? "—"}</span>
    </div>
  );
}

function TitrationNotes({ context }: { context: string | null }) {
  const [open, setOpen] = useState(false);
  if (!context) return <span className="text-[#4b5563]">—</span>;
  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-[11px] text-[#4CA9EF] hover:underline"
      >
        {open ? "Hide" : "Show"}
      </button>
      {open && (
        <p className="mt-1 text-[11px] text-[#9ca3af] leading-relaxed max-w-xs">{context}</p>
      )}
    </div>
  );
}

export default function DosingPage() {
  const [data, setData] = useState<DosingProtocol[]>([]);
  const [loading, setLoading] = useState(true);
  const [sourceFilter, setSourceFilter] = useState("all");
  const [minConfidence, setMinConfidence] = useState(0);
  const [sortKey, setSortKey] = useState<"dose" | "confidence" | "source_type">("confidence");

  useEffect(() => {
    const params: Record<string, string | number | undefined> = {};
    if (sourceFilter !== "all") params.source_type = sourceFilter;
    if (minConfidence > 0) params.min_confidence = minConfidence;
    setLoading(true);
    api.dosing(params as Parameters<typeof api.dosing>[0]).then((d) => {
      setData(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [sourceFilter, minConfidence]);

  const sorted = [...data].sort((a, b) => {
    if (sortKey === "confidence") {
      const order: Record<string, number> = { high: 0, medium: 1, low: 2 };
      return (order[a.confidence?.toLowerCase() ?? ""] ?? 3) - (order[b.confidence?.toLowerCase() ?? ""] ?? 3);
    }
    if (sortKey === "source_type") return (a.source_type ?? "").localeCompare(b.source_type ?? "");
    return (a.dose ?? "").localeCompare(b.dose ?? "");
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Dosing Protocols</h1>
        <p className="text-sm text-[#6b7280] mt-0.5">Extracted dosing regimens from all sources</p>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3 items-center rounded-xl border p-3" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2">
          <label className="text-[10px] uppercase tracking-wider text-[#6b7280]">Source</label>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="text-xs rounded-lg px-2 py-1.5 text-white focus:outline-none"
            style={{ background: "var(--bg-base)", border: "1px solid var(--border)" }}
          >
            {SOURCE_TYPES.map((s) => (
              <option key={s} value={s}>{s === "all" ? "All sources" : s}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-[10px] uppercase tracking-wider text-[#6b7280]">
            Min confidence: <span className="text-white">{minConfidence.toFixed(1)}</span>
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={minConfidence}
            onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
            className="w-28 accent-[#0047BB]"
          />
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <label className="text-[10px] uppercase tracking-wider text-[#6b7280]">Sort</label>
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as typeof sortKey)}
            className="text-xs rounded-lg px-2 py-1.5 text-white focus:outline-none"
            style={{ background: "var(--bg-base)", border: "1px solid var(--border)" }}
          >
            <option value="confidence">Confidence</option>
            <option value="dose">Dose</option>
            <option value="source_type">Source</option>
          </select>
        </div>
      </div>

      {/* Chart */}
      {!loading && data.length > 0 && (
        <div className="rounded-xl border p-4" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <h2 className="text-xs uppercase tracking-widest text-[#6b7280] font-medium mb-4">Dose Distribution</h2>
          <DosingDistributionChart data={data} />
        </div>
      )}

      {/* Table */}
      {loading ? (
        <LoadingGrid count={6} />
      ) : sorted.length === 0 ? (
        <EmptyState icon={FlaskConical} title="No protocols found" description="Adjust filters or run the synthesis pipeline." />
      ) : (
        <div className="rounded-xl border overflow-hidden" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b" style={{ borderColor: "var(--border)" }}>
                  {["Dose", "Unit", "Frequency", "Route", "Source", "Confidence", "Titration Notes"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-[#4b5563] font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((row) => (
                  <tr key={row.id} className="border-b transition-colors hover:bg-white/[0.02]" style={{ borderColor: "var(--border)" }}>
                    <td className="px-4 py-3 text-white font-mono">{row.dose ?? "—"}</td>
                    <td className="px-4 py-3 text-[#9ca3af]">mg</td>
                    <td className="px-4 py-3 text-[#9ca3af]">{row.frequency ?? "—"}</td>
                    <td className="px-4 py-3 text-[#9ca3af]">{row.route ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ background: "rgba(0,71,187,0.15)", color: "#4CA9EF" }}>
                        {row.source_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 w-36"><ConfidenceBar value={row.confidence} /></td>
                    <td className="px-4 py-3"><TitrationNotes context={row.context} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
