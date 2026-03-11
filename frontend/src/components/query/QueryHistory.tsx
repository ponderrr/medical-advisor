"use client";

import { History, Trash2 } from "lucide-react";
import type { HistoryItem } from "@/hooks/useQuery";

interface Props {
  history: HistoryItem[];
  onSelect: (item: HistoryItem) => void;
  onClear: () => void;
}

export function QueryHistory({ history, onSelect, onClear }: Props) {
  if (history.length === 0) return null;

  return (
    <div
      className="rounded-xl border"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2 text-xs font-medium text-[#9ca3af]">
          <History size={14} />
          Recent Queries
        </div>
        <button
          onClick={onClear}
          className="text-[#4b5563] hover:text-[#9ca3af] transition-colors"
          title="Clear history"
        >
          <Trash2 size={13} />
        </button>
      </div>
      <ul className="py-1">
        {history.map((item, i) => (
          <li key={i}>
            <button
              onClick={() => onSelect(item)}
              className="w-full text-left px-4 py-2.5 hover:bg-white/5 transition-colors"
            >
              <p className="text-xs text-white truncate max-w-[180px]">
                {item.question.slice(0, 40)}{item.question.length > 40 ? "…" : ""}
              </p>
              <p className="text-[10px] text-[#4b5563] mt-0.5">
                {item.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
