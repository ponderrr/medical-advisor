"use client";

import { useRef, useEffect, KeyboardEvent } from "react";
import { clsx } from "clsx";
import { Send } from "lucide-react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
}

export function QueryInput({ value, onChange, onSubmit, loading }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  // Auto-resize
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 144)}px`; // max ~6 rows
  }, [value]);

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (canSubmit) onSubmit();
    }
  }

  const canSubmit = value.length >= 10 && value.length <= 500 && !loading;
  const overLimit = value.length > 450;

  return (
    <div
      className="rounded-xl border p-3 transition-colors focus-within:border-[#4CA9EF]/60"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Ask about dosing protocols, side effects, mechanisms, or known conflicts..."
        rows={2}
        maxLength={500}
        className="w-full bg-transparent text-white text-sm resize-none outline-none placeholder:text-[#4b5563] leading-relaxed"
        style={{ minHeight: "3rem" }}
        disabled={loading}
      />
      <div className="flex items-center justify-between mt-2">
        <span
          className={clsx(
            "text-xs",
            overLimit ? "text-red-400" : "text-[#4b5563]",
          )}
        >
          {value.length}/500
        </span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#4b5563] hidden sm:block">⌘ + Enter</span>
          <button
            onClick={onSubmit}
            disabled={!canSubmit}
            className={clsx(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-all",
              canSubmit
                ? "opacity-100 hover:opacity-80"
                : "opacity-30 cursor-not-allowed",
            )}
            style={{ background: canSubmit ? "var(--cta)" : "#374151" }}
          >
            {loading ? (
              <span className="animate-pulse">…</span>
            ) : (
              <>
                <Send size={13} /> Send
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
