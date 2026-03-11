"use client";

import { useState, useCallback } from "react";
import { api, ApiError } from "@/lib/api";
import type { QueryResponse } from "@/types/api";

export interface HistoryItem {
  question: string;
  response: QueryResponse;
  timestamp: Date;
}

export function useQuery() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ status?: number; message: string } | null>(null);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [lastQuestion, setLastQuestion] = useState("");

  const submit = useCallback(async (question: string) => {
    setLoading(true);
    setError(null);
    setLastQuestion(question);

    try {
      const res = await api.query({ question, max_context_rows: 20 });
      setResponse(res);
      setHistory((prev) =>
        [{ question, response: res, timestamp: new Date() }, ...prev].slice(0, 10),
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ status: err.status, message: err.message });
      } else {
        setError({ message: "Network error. Please try again." });
      }
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const retry = useCallback(() => {
    if (lastQuestion) submit(lastQuestion);
  }, [lastQuestion, submit]);

  const clearHistory = useCallback(() => setHistory([]), []);

  const restoreFromHistory = useCallback((item: HistoryItem) => {
    setResponse(item.response);
    setError(null);
  }, []);

  return { loading, error, response, history, submit, retry, clearHistory, restoreFromHistory };
}
