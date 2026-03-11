"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Mechanism } from "@/types/api";
import { LoadingGrid } from "@/components/ui/LoadingCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { GitMerge } from "lucide-react";

const RECEPTORS = ["GLP-1R", "GIPR", "GcgR"];
const EVIDENCE_LEVELS = ["all", "high", "medium", "low"];

const RECEPTOR_COLORS: Record<string, { bg: string; text: string }> = {
  "GLP-1R": { bg: "rgba(0,71,187,0.2)",   text: "#4CA9EF" },
  "GIPR":   { bg: "rgba(232,119,34,0.2)",  text: "#E87722" },
  "GcgR":   { bg: "rgba(34,197,94,0.15)",  text: "#22c55e" },
};

function ReceptorPills({ mechanism }: { mechanism: string }) {
  const matched = RECEPTORS.filter((r) => mechanism.toUpperCase().includes(r.toUpperCase()));
  return (
    <div className="flex flex-wrap gap-1">
      {matched.length > 0 ? matched.map((r) => {
        const style = RECEPTOR_COLORS[r] ?? { bg: "rgba(255,255,255,0.08)", text: "#9ca3af" };
        return (
          <span key={r} className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium" style={{ background: style.bg, color: style.text }}>
            {r}
          </span>
        );
      }) : (
        <span className="text-[10px] text-[#4b5563]">unknown</span>
      )}
    </div>
  );
}

function ConfidenceDot({ confidence }: { confidence: string | null }) {
  const map: Record<string, string> = { high: "#22c55e", medium: "#f59e0b", low: "#ef4444" };
  const color = map[confidence?.toLowerCase() ?? ""] ?? "#4b5563";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-2 h-2 rounded-full" style={{ background: color }} />
      <span className="text-[11px] text-[#6b7280]">{confidence ?? "unknown"}</span>
    </div>
  );
}

export default function MechanismsPage() {
  const [data, setData] = useState<Mechanism[]>([]);
  const [loading, setLoading] = useState(true);
  const [receptorFilter, setReceptorFilter] = useState<string | null>(null);
  const [evidenceFilter, setEvidenceFilter] = useState("all");

  useEffect(() => {
    api.mechanisms({ receptor: receptorFilter ?? undefined, limit: 50 }).then((d) => {
      setData(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [receptorFilter]);

  const filtered = evidenceFilter === "all"
    ? data
    : data.filter((m) => m.confidence?.toLowerCase() === evidenceFilter);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Mechanisms of Action</h1>
        <p className="text-sm text-[#6b7280] mt-0.5">Pharmacological mechanisms extracted from literature</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center rounded-xl border p-3" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-[#4b5563]">Receptor:</span>
          <button
            onClick={() => setReceptorFilter(null)}
            className="px-2.5 py-1 rounded-full text-xs transition-all"
            style={{
              background: receptorFilter === null ? "rgba(0,71,187,0.2)" : "transparent",
              color: receptorFilter === null ? "#4CA9EF" : "#6b7280",
              border: `1px solid ${receptorFilter === null ? "#0047BB" : "var(--border)"}`,
            }}
          >
            All
          </button>
          {RECEPTORS.map((r) => {
            const active = receptorFilter === r;
            const style = RECEPTOR_COLORS[r];
            return (
              <button
                key={r}
                onClick={() => setReceptorFilter(active ? null : r)}
                className="px-2.5 py-1 rounded-full text-xs font-mono font-medium transition-all"
                style={{
                  background: active ? style.bg : "transparent",
                  color: active ? style.text : "#6b7280",
                  border: `1px solid ${active ? style.text : "var(--border)"}`,
                }}
              >
                {r}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-[10px] uppercase tracking-wider text-[#4b5563]">Evidence:</span>
          <select
            value={evidenceFilter}
            onChange={(e) => setEvidenceFilter(e.target.value)}
            className="text-xs rounded-lg px-2 py-1.5 text-white focus:outline-none"
            style={{ background: "var(--bg-base)", border: "1px solid var(--border)" }}
          >
            {EVIDENCE_LEVELS.map((l) => (
              <option key={l} value={l}>{l === "all" ? "All evidence" : l}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Cards */}
      {loading ? (
        <LoadingGrid count={6} />
      ) : filtered.length === 0 ? (
        <EmptyState icon={GitMerge} title="No mechanisms found" description="Try adjusting receptor or evidence filters." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {filtered.map((m) => (
            <div
              key={m.id}
              className="rounded-xl border p-4 space-y-3 transition-colors hover:border-[#0047BB]/40"
              style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-semibold text-white leading-snug">{m.mechanism}</h3>
                <ConfidenceDot confidence={m.confidence} />
              </div>
              <p className="text-xs text-[#9ca3af] leading-relaxed">{m.description}</p>
              <div className="flex items-center justify-between pt-1">
                <ReceptorPills mechanism={m.mechanism} />
                {m.sources && m.sources.length > 0 && (
                  <span className="text-[10px] text-[#4b5563]">{m.sources.length} source{m.sources.length !== 1 ? "s" : ""}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
