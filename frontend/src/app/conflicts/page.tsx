"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Conflict } from "@/types/api";
import { LoadingGrid } from "@/components/ui/LoadingCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { AlertTriangle, ChevronDown, ChevronRight } from "lucide-react";

const TABS = ["All", "Minor", "Major", "Critical"] as const;
type Tab = (typeof TABS)[number];

const SEVERITY_STYLE: Record<string, { bg: string; text: string }> = {
  minor:    { bg: "rgba(34,197,94,0.12)",   text: "#22c55e" },
  major:    { bg: "rgba(245,158,11,0.12)",  text: "#f59e0b" },
  critical: { bg: "rgba(239,68,68,0.12)",   text: "#ef4444" },
};

function inferSeverity(c: Conflict): string {
  const text = `${c.topic} ${c.description ?? ""}`.toLowerCase();
  if (text.includes("critical") || text.includes("dangerous") || text.includes("fatal")) return "critical";
  if (text.includes("major") || text.includes("significant") || text.includes("serious")) return "major";
  return "minor";
}

function ConflictRow({ conflict }: { conflict: Conflict }) {
  const [open, setOpen] = useState(false);
  const sev = inferSeverity(conflict);
  const style = SEVERITY_STYLE[sev] ?? SEVERITY_STYLE.minor;

  return (
    <div className="border-b last:border-0" style={{ borderColor: "var(--border)" }}>
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown size={14} className="text-[#4b5563] shrink-0" /> : <ChevronRight size={14} className="text-[#4b5563] shrink-0" />}
        <span className="flex-1 text-sm text-white font-medium">{conflict.topic}</span>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ background: style.bg, color: style.text }}>
          {sev}
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 ml-5">
          {conflict.description && (
            <p className="text-xs text-[#9ca3af] leading-relaxed">{conflict.description}</p>
          )}
          <div className="grid md:grid-cols-2 gap-3">
            {conflict.source_a_claim && (
              <div className="rounded-lg p-3" style={{ background: "rgba(0,71,187,0.08)", border: "1px solid rgba(0,71,187,0.2)" }}>
                <div className="text-[10px] uppercase tracking-wider text-[#4CA9EF] mb-1.5">
                  Source A {conflict.source_a_type ? `· ${conflict.source_a_type}` : ""}
                </div>
                <p className="text-xs text-[#d1d5db]">{conflict.source_a_claim}</p>
              </div>
            )}
            {conflict.source_b_claim && (
              <div className="rounded-lg p-3" style={{ background: "rgba(232,119,34,0.08)", border: "1px solid rgba(232,119,34,0.2)" }}>
                <div className="text-[10px] uppercase tracking-wider text-[#E87722] mb-1.5">
                  Source B {conflict.source_b_type ? `· ${conflict.source_b_type}` : ""}
                </div>
                <p className="text-xs text-[#d1d5db]">{conflict.source_b_claim}</p>
              </div>
            )}
          </div>
          {conflict.resolution && (
            <div className="rounded-lg p-3" style={{ background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.15)" }}>
              <div className="text-[10px] uppercase tracking-wider text-[#22c55e] mb-1.5">Resolution</div>
              <p className="text-xs text-[#d1d5db]">{conflict.resolution}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ConflictsPage() {
  const [data, setData] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("All");

  useEffect(() => {
    api.conflicts({ limit: 100 }).then((d) => {
      setData(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const filtered = tab === "All" ? data : data.filter((c) => inferSeverity(c) === tab.toLowerCase());

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Data Conflicts</h1>
        <p className="text-sm text-[#6b7280] mt-0.5">Contradictions detected between data sources</p>
      </div>

      {/* Severity tabs */}
      <div className="flex gap-1 rounded-xl border p-1" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="flex-1 text-xs py-1.5 rounded-lg transition-colors font-medium"
            style={{
              background: tab === t ? "rgba(255,255,255,0.08)" : "transparent",
              color: tab === t ? "#fff" : "#6b7280",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingGrid count={4} />
      ) : filtered.length === 0 ? (
        <EmptyState icon={AlertTriangle} title="No conflicts found" description="No conflicts match the selected severity." />
      ) : (
        <div className="rounded-xl border overflow-hidden" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
          {filtered.map((c) => (
            <ConflictRow key={c.id} conflict={c} />
          ))}
        </div>
      )}
    </div>
  );
}
