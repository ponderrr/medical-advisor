"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SideEffect } from "@/types/api";
import { SideEffectBarChart } from "@/components/charts/SideEffectBarChart";
import { LoadingGrid } from "@/components/ui/LoadingCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { AlertTriangle } from "lucide-react";

const SEVERITIES = ["mild", "moderate", "severe", "critical"];

const SEVERITY_COLORS: Record<string, { bg: string; text: string }> = {
  mild:     { bg: "rgba(34,197,94,0.15)",   text: "#22c55e" },
  moderate: { bg: "rgba(245,158,11,0.15)",  text: "#f59e0b" },
  severe:   { bg: "rgba(239,68,68,0.15)",   text: "#ef4444" },
  critical: { bg: "rgba(168,85,247,0.15)",  text: "#a855f7" },
};

function SeverityBadge({ severity }: { severity: string | null }) {
  const key = severity?.toLowerCase() ?? "";
  const style = SEVERITY_COLORS[key] ?? { bg: "rgba(255,255,255,0.08)", text: "#9ca3af" };
  return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ background: style.bg, color: style.text }}>
      {severity ?? "unknown"}
    </span>
  );
}

export default function SideEffectsPage() {
  const [data, setData] = useState<SideEffect[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.sideEffects({ limit: 50 }).then((d) => {
      setData(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const toggle = (s: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s); else next.add(s);
      return next;
    });
  };

  const filtered = selected.size === 0
    ? data
    : data.filter((d) => selected.has(d.severity?.toLowerCase() ?? "unknown"));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Side Effects</h1>
        <p className="text-sm text-[#6b7280] mt-0.5">Aggregated adverse events from literature and user reports</p>
      </div>

      {/* Severity multiselect */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-[10px] uppercase tracking-wider text-[#4b5563]">Filter:</span>
        {SEVERITIES.map((s) => {
          const active = selected.has(s);
          const style = SEVERITY_COLORS[s];
          return (
            <button
              key={s}
              onClick={() => toggle(s)}
              className="px-3 py-1 rounded-full text-xs font-medium transition-all"
              style={{
                background: active ? style.bg : "transparent",
                color: active ? style.text : "#6b7280",
                border: `1px solid ${active ? style.text : "var(--border)"}`,
              }}
            >
              {s}
            </button>
          );
        })}
        {selected.size > 0 && (
          <button onClick={() => setSelected(new Set())} className="text-[11px] text-[#4CA9EF] hover:underline ml-1">
            Clear
          </button>
        )}
      </div>

      {/* Chart */}
      {!loading && filtered.length > 0 && (
        <div className="rounded-xl border p-4" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <h2 className="text-xs uppercase tracking-widest text-[#6b7280] font-medium mb-4">Frequency by Effect</h2>
          <SideEffectBarChart data={filtered} />
        </div>
      )}

      {/* Table */}
      {loading ? (
        <LoadingGrid count={6} />
      ) : filtered.length === 0 ? (
        <EmptyState icon={AlertTriangle} title="No side effects found" description="No data matches the selected filters." />
      ) : (
        <div className="rounded-xl border overflow-hidden" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b" style={{ borderColor: "var(--border)" }}>
                  {["Effect", "Severity", "Frequency", "Context"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-[#4b5563] font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.sort((a, b) => b.frequency - a.frequency).map((row) => (
                  <tr key={row.id} className="border-b transition-colors hover:bg-white/[0.02]" style={{ borderColor: "var(--border)" }}>
                    <td className="px-4 py-3 text-white font-medium">{row.effect}</td>
                    <td className="px-4 py-3"><SeverityBadge severity={row.severity} /></td>
                    <td className="px-4 py-3 text-[#9ca3af] font-mono">{row.frequency}×</td>
                    <td className="px-4 py-3 text-[#6b7280] max-w-sm">
                      {row.description ? (
                        <span className="italic line-clamp-2">&ldquo;{row.description}&rdquo;</span>
                      ) : "—"}
                    </td>
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
