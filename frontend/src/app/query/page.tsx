"use client";

import { useState } from "react";
import { useQuery } from "@/hooks/useQuery";
import { QueryInput } from "@/components/query/QueryInput";
import { QueryResponse } from "@/components/query/QueryResponse";
import { QueryHistory } from "@/components/query/QueryHistory";
import { SuggestedQueries } from "@/components/query/SuggestedQueries";
import { AlertTriangle, WifiOff } from "lucide-react";

export default function QueryPage() {
  const { loading, error, response, history, submit, retry, clearHistory, restoreFromHistory } = useQuery();
  const [question, setQuestion] = useState("");

  // QueryInput.onSubmit is () => void — it uses the value prop
  const handleSubmit = () => {
    const q = question;
    setQuestion("");
    submit(q);
  };

  const isRateLimit = error?.status === 429;
  const isNetworkError = error !== null && !isRateLimit;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-white">Research Query</h1>
        <p className="text-sm text-[#6b7280] mt-0.5">Ask anything about Retatrutide based on synthesised data</p>
      </div>

      {/* Error banners */}
      {isRateLimit && (
        <div className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm" style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", color: "#f59e0b" }}>
          <AlertTriangle size={16} className="shrink-0" />
          <span>Rate limit reached — max 10 requests per minute. Please wait before trying again.</span>
          <button onClick={retry} className="ml-auto text-xs underline shrink-0">Retry</button>
        </div>
      )}
      {isNetworkError && (
        <div className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444" }}>
          <WifiOff size={16} className="shrink-0" />
          <span>{error?.message ?? "Network error. Check the backend is running."}</span>
          <button onClick={retry} className="ml-auto text-xs underline shrink-0">Retry</button>
        </div>
      )}

      {/* Two-column layout */}
      <div className="grid gap-4 md:grid-cols-[1fr_280px]">
        {/* Main column */}
        <div className="space-y-4 min-w-0">
          <QueryInput
            value={question}
            onChange={setQuestion}
            onSubmit={handleSubmit}
            loading={loading}
          />

          {(loading || response) && (
            <QueryResponse response={response} loading={loading} />
          )}

          {!response && !loading && (
            <div className="rounded-xl border p-8 text-center" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
              <p className="text-sm text-[#4b5563]">Ask a question above to get AI-synthesised insights from Retatrutide research data.</p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <div className="rounded-xl border p-4" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
            <SuggestedQueries onSelect={setQuestion} />
          </div>

          {history.length > 0 && (
            <QueryHistory
              history={history}
              onSelect={restoreFromHistory}
              onClear={clearHistory}
            />
          )}
        </div>
      </div>
    </div>
  );
}
