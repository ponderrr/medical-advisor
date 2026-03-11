"use client";

import { useEffect, useState } from "react";
import { FileText, FlaskConical, AlertTriangle, GitMerge } from "lucide-react";
import { api } from "@/lib/api";
import type { Conflict, SideEffect, SynthesisSummary, StatsResponse } from "@/types/api";
import { DataCard } from "@/components/cards/DataCard";
import { SideEffectBarChart } from "@/components/charts/SideEffectBarChart";
import { ReceptorCoverageChart } from "@/components/charts/ReceptorCoverageChart";
import { LoadingGrid } from "@/components/ui/LoadingCard";

function ConflictPreview() {
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  useEffect(() => { api.conflicts({ limit: 5 }).then(setConflicts).catch(() => {}); }, []);
  return (
    <ul className="divide-y" style={{ borderColor: "var(--border)" }}>
      {conflicts.map((c) => (
        <li key={c.id} className="px-4 py-3">
          <span className="text-[10px] px-2 py-0.5 rounded-full font-medium" style={{ background: "#E877221A", color: "#E87722" }}>{c.topic}</span>
          <p className="text-xs text-[#9ca3af] mt-1 line-clamp-2">{c.description}</p>
        </li>
      ))}
      {conflicts.length === 0 && <li className="px-4 py-6 text-center text-xs text-[#4b5563]">No conflicts detected</li>}
    </ul>
  );
}

export default function OverviewPage() {
  const [summary, setSummary] = useState<SynthesisSummary | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [sideEffects, setSideEffects] = useState<SideEffect[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([api.summary().catch(() => null), api.stats().catch(() => null), api.sideEffects({ limit: 10 }).catch(() => [] as SideEffect[])]).then(([s, st, se]) => {
      setSummary(s); setStats(st); setSideEffects(se ?? []); setLoading(false);
    });
  }, []);
  return (
    <div className="space-y-6">
      <div><h1 className="text-xl font-bold text-white">Overview</h1><p className="text-sm text-[#6b7280] mt-0.5">Synthesis dashboard for Retatrutide research data</p></div>
      {loading ? <LoadingGrid count={4} /> : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <DataCard title="Research Papers" value={stats?.total_papers ?? 0} icon={FileText} subtitle="PubMed" />
          <DataCard title="Clinical Trials" value={stats?.total_trials ?? 0} icon={FlaskConical} subtitle="ClinicalTrials.gov" />
          <DataCard title="Side Effects" value={summary?.total_side_effects ?? 0} icon={AlertTriangle} subtitle="Tracked" />
          <DataCard title="Conflicts" value={summary?.total_conflicts ?? 0} icon={GitMerge} subtitle="Detected" />
        </div>
      )}
      {!loading && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border p-4" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
            <h2 className="text-xs uppercase tracking-widest text-[#6b7280] font-medium mb-4">Top Side Effects</h2>
            <SideEffectBarChart data={sideEffects} />
          </div>
          <div className="rounded-xl border p-4" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
            <h2 className="text-xs uppercase tracking-widest text-[#6b7280] font-medium mb-4">Receptor Coverage</h2>
            <ReceptorCoverageChart data={summary?.receptor_coverage ?? []} totalMechanisms={summary?.total_mechanisms ?? 0} />
          </div>
        </div>
      )}
      {!loading && (<div className="rounded-xl border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}><div className="px-4 py-3 border-b" style={{ borderColor: "var(--border)" }}><h2 className="text-xs uppercase tracking-widest text-[#6b7280] font-medium">Recent Conflicts</h2></div><ConflictPreview /></div>)}
    </div>
  );
}
