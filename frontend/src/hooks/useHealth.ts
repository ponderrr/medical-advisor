"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { HealthResponse } from "@/types/api";

export function useHealth(pollIntervalMs = 30_000) {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchHealth() {
      try {
        const data = await api.health();
        if (!cancelled) setHealth(data);
      } catch {
        // silently ignore — badge will just stay in last known state
      }
    }

    fetchHealth();
    const id = setInterval(fetchHealth, pollIntervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollIntervalMs]);

  return health;
}
