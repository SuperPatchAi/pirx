"use client";

import { useEffect, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { useProjectionStore } from "@/stores/projection-store";
import type { RealtimePostgresChangesPayload } from "@supabase/supabase-js";

const DRIVER_KEYS = [
  "aerobic_base",
  "threshold_density",
  "speed_exposure",
  "running_economy",
  "load_consistency",
] as const;

const DRIVER_DISPLAY_NAMES: Record<string, string> = {
  aerobic_base: "Aerobic Base",
  threshold_density: "Threshold Density",
  speed_exposure: "Speed Exposure",
  running_economy: "Running Economy",
  load_consistency: "Load Consistency",
};

type DriverTrend = "improving" | "stable" | "declining";

function rowToDrivers(row: Record<string, unknown>) {
  return DRIVER_KEYS.map((key) => {
    const contribution = (row[`${key}_seconds`] as number) ?? 0;
    const score = (row[`${key}_score`] as number) ?? 50;
    const trend = (row[`${key}_trend`] as DriverTrend) ?? "stable";
    return {
      name: key,
      displayName: DRIVER_DISPLAY_NAMES[key] ?? key,
      contributionSeconds: contribution,
      score,
      trend,
    };
  });
}

export function useProjectionRealtime(userId: string | null) {
  const setProjection = useProjectionStore((s) => s.setProjection);
  const setDrivers = useProjectionStore((s) => s.setDrivers);

  const handleProjectionChange = useCallback(
    (payload: RealtimePostgresChangesPayload<Record<string, unknown>>) => {
      if (payload.eventType === "INSERT" && payload.new) {
        const row = payload.new as Record<string, unknown>;
        setProjection({
          projectedTimeSeconds: (row.midpoint_seconds ?? 0) as number,
          rangeLower: (row.range_low_seconds ?? row.range_lower ?? 0) as number,
          rangeUpper: (row.range_high_seconds ?? row.range_upper ?? 0) as number,
          improvementSeconds: (row.improvement_since_baseline ?? 0) as number,
          twentyOneDayChange: (row.twenty_one_day_change ?? 0) as number,
          volatility: (row.volatility ?? row.volatility_score ?? 0) as number,
          lastUpdated: (row.computed_at ?? "") as string,
        });
      }
    },
    [setProjection]
  );

  const handleDriverChange = useCallback(
    (payload: RealtimePostgresChangesPayload<Record<string, unknown>>) => {
      if (payload.eventType === "INSERT" && payload.new) {
        const row = payload.new as Record<string, unknown>;
        setDrivers(rowToDrivers(row));
      }
    },
    [setDrivers]
  );

  useEffect(() => {
    if (!userId) return;

    const supabase = createClient();

    const channel = supabase
      .channel(`projection-${userId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "projection_state",
          filter: `user_id=eq.${userId}`,
        },
        handleProjectionChange
      )
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "driver_state",
          filter: `user_id=eq.${userId}`,
        },
        handleDriverChange
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId, handleProjectionChange, handleDriverChange]);
}
