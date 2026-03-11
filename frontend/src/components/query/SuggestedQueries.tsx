"use client";

import { Sparkles } from "lucide-react";

const SUGGESTIONS = [
  "What are the most reported side effects of Retatrutide?",
  "What dosing protocols appear most frequently in clinical trials?",
  "How does Retatrutide's glucagon receptor activity differ from GLP-1?",
  "Are there any dosing conflicts between literature and user reports?",
  "What evidence level exists for Retatrutide's weight loss mechanism?",
  "What are the critical safety conflicts in the data?",
];

interface Props {
  onSelect: (q: string) => void;
}

export function SuggestedQueries({ onSelect }: Props) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-[#4b5563] font-medium">
        <Sparkles size={11} />
        Suggested Questions
      </div>
      <div className="grid gap-2">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="text-left text-xs text-[#9ca3af] hover:text-white rounded-lg px-3 py-2.5 border transition-colors hover:border-[#0047BB]/50"
            style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
