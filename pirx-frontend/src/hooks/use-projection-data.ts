"use client";

import { useEffect, useState } from "react";
import { useProjectionStore } from "@/stores/projection-store";
import { useAuth } from "@/hooks/use-auth";
import { useProjectionRealtime } from "@/hooks/use-projection-realtime";

export function useProjectionData() {
  const { user } = useAuth();
  const store = useProjectionStore();
  const [loading, setLoading] = useState(true);

  // Subscribe to realtime updates
  useProjectionRealtime(user?.id ?? null);

  // Fetch initial data
  useEffect(() => {
    if (!user) return;

    async function fetchProjection() {
      try {
        const { apiFetch } = await import("@/lib/api");
        const data = await apiFetch(
          `/projection?event=${store.currentEvent}`
        ) as {
          projected_time_seconds?: number;
          supported_range_low?: number;
          supported_range_high?: number;
          total_improvement_seconds?: number;
          twenty_one_day_change?: number;
          volatility?: number;
          last_updated?: string;
        };
        store.setProjection({
          projectedTimeSeconds: data.projected_time_seconds ?? null,
          rangeLower: data.supported_range_low ?? null,
          rangeUpper: data.supported_range_high ?? null,
          improvementSeconds: data.total_improvement_seconds ?? null,
          twentyOneDayChange: data.twenty_one_day_change ?? 0,
          volatility: data.volatility ?? null,
          lastUpdated: data.last_updated ?? null,
        });
      } catch {
        // API not available, use mock data
      } finally {
        setLoading(false);
      }
    }

    fetchProjection();
  }, [user, store.currentEvent]);

  return { loading, ...store };
}
