"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { clsx } from "clsx";
import { ChevronDown } from "lucide-react";
import type { QueryResponse } from "@/types/api";

interface Props {
  response: QueryResponse | null;
  loading: boolean;
}

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.8 ? "#22c55e" : value >= 0.5 ? "#E87722" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 rounded-full overflow-hidden h-1.5" style={{ background: "rgba(255,255,255,0.08)" }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs text-[#6b7280] w-10 text-right">{pct}%</span>
    </div>
  );
}

export function QueryResponse({ response, loading }: Props) {
  const [sourcesOpen, setSourcesOpen] = useState(false);

  if (loading) {
    return (
      <div
        className="rounded-xl border p-6"
        style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2 text-[#4CA9EF] text-sm">
          <span>Analyzing sources</span>
          <span className="animate-pulse">
            <span>.</span>
            <span style={{ animationDelay: "0.2s" }}>.</span>
            <span style={{ animationDelay: "0.4s" }}>.</span>
          </span>
        </div>
      </div>
    );
  }

  if (!response) return null;

  return (
    <div
      className="rounded-xl border divide-y"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      {/* Answer */}
      <div className="p-5">
        <div className="prose prose-sm prose-invert max-w-none text-[#d1d5db] leading-relaxed">
          <ReactMarkdown>{response.answer}</ReactMarkdown>
        </div>
      </div>

      {/* Meta row */}
      <div className="px-5 py-3 flex flex-wrap gap-4 items-center" style={{ borderColor: "var(--border)" }}>
        {/* Domains */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {response.domains_covered.map((d) => (
            <span
              key={d}
              className="text-[10px] px-2 py-0.5 rounded-full border font-medium"
              style={{ borderColor: "var(--brand)", color: "#4CA9EF", background: "#0047BB1A" }}
            >
              {d}
            </span>
          ))}
        </div>

        {/* Confidence */}
        <div className="flex-1 min-w-32">
          <p className="text-[10px] text-[#6b7280] mb-1 uppercase tracking-wider">Confidence</p>
          <ConfidenceMeter value={response.confidence} />
        </div>

        {/* Sources toggle */}
        {response.sources_used.length > 0 && (
          <button
            onClick={() => setSourcesOpen((o) => !o)}
            className="flex items-center gap-1 text-xs text-[#6b7280] hover:text-white transition-colors"
          >
            {response.sources_used.length} source{response.sources_used.length !== 1 ? "s" : ""}
            <ChevronDown size={13} className={clsx("transition-transform", sourcesOpen && "rotate-180")} />
          </button>
        )}
      </div>

      {/* Sources */}
      {sourcesOpen && response.sources_used.length > 0 && (
        <div className="px-5 py-3" style={{ borderColor: "var(--border)" }}>
          <ul className="space-y-1">
            {response.sources_used.map((s, i) => (
              <li key={i} className="text-xs text-[#9ca3af]">• {s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Disclaimer */}
      <div className="px-5 py-3" style={{ borderColor: "var(--border)" }}>
        <p className="text-xs italic text-[#4b5563]">{response.disclaimer}</p>
      </div>
    </div>
  );
}
