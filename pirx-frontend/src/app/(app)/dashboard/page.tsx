"use client";

import { useState, useEffect, useCallback } from "react";
import { ProjectionTile } from "@/components/home/projection-tile";
import { EventSwiper } from "@/components/home/event-swiper";
import { DriverStrip, type DriverApiItem } from "@/components/home/driver-strip";
import { QuickMetrics } from "@/components/home/quick-metrics";
import { SyncBanner } from "@/components/home/sync-banner";
import { useProjectionRealtime } from "@/hooks/use-projection-realtime";
import { useProjectionStore } from "@/stores/projection-store";
import { useAuth } from "@/hooks/use-auth";
import { Loader2 } from "lucide-react";

// Mock data as fallback
const MOCK_PROJECTION = {
  projected_time: "19:42",
  supported_range: "19:15 – 20:08",
  total_improvement_seconds: 78,
  twenty_one_day_change: 5,
};

function formatTime(seconds: number): string {
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.round(seconds % 60);
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [projection, setProjection] = useState<Record<string, unknown> | null>(null);
  const [drivers, setDrivers] = useState<DriverApiItem[] | null>(null);
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [selectedEvent, setSelectedEvent] = useState("5000");

  const { user } = useAuth();
  useProjectionRealtime(user?.id ?? null);

  const storeProjectionTime = useProjectionStore((s) => s.projectedTimeSeconds);
  const storeDrivers = useProjectionStore((s) => s.drivers);

  useEffect(() => {
    if (storeProjectionTime !== null) {
      const store = useProjectionStore.getState();
      setProjection({
        projected_time_seconds: store.projectedTimeSeconds,
        supported_range_low: store.rangeLower,
        supported_range_high: store.rangeUpper,
        total_improvement_seconds: store.improvementSeconds,
        twenty_one_day_change: store.twentyOneDayChange,
      } as Record<string, unknown>);
    }
  }, [storeProjectionTime]);

  useEffect(() => {
    if (storeDrivers.length > 0) {
      setDrivers(storeDrivers);
    }
  }, [storeDrivers]);

  const fetchProjection = useCallback(async (event: string) => {
    try {
      const { apiFetch } = await import("@/lib/api");
      const projData = await apiFetch(`/projection?event=${event}`);
      setProjection(projData as Record<string, unknown>);
    } catch {
      /* keep existing data */
    }
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const { apiFetch } = await import("@/lib/api");
        const [projData, driversData, readinessData] = await Promise.allSettled([
          apiFetch(`/projection?event=${selectedEvent}`),
          apiFetch("/drivers"),
          apiFetch("/readiness"),
        ]);

        if (projData.status === "fulfilled") setProjection(projData.value as Record<string, unknown>);
        if (driversData.status === "fulfilled") {
          const res = driversData.value as { drivers?: Array<{ driver_name?: string; display_name?: string; contribution_seconds?: number; trend?: string; score?: number }> };
          const list = res?.drivers ?? [];
          type Trend = "improving" | "stable" | "declining";
          const toTrend = (s: string | undefined): Trend => (s === "improving" || s === "declining" ? s : "stable");
          setDrivers(
            list.map((d) => ({
              name: d.driver_name ?? "",
              displayName: d.display_name ?? "",
              contributionSeconds: d.contribution_seconds ?? 0,
              trend: toTrend(d.trend),
              score: d.score ?? 0,
            }))
          );
        }
        if (readinessData.status === "fulfilled") setReadiness(readinessData.value as Record<string, unknown>);
      } catch {
        // Use mock data on failure
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleEventSelect = useCallback(
    (event: string) => {
      setSelectedEvent(event);
      fetchProjection(event);
    },
    [fetchProjection]
  );

  const projTime = projection
    ? (projection.projected_time_display as string) ?? formatTime(projection.projected_time_seconds as number)
    : MOCK_PROJECTION.projected_time;
  const projRange = projection
    ? ((projection.supported_range_display as string) ?? `${formatTime(projection.supported_range_low as number)} – ${formatTime(projection.supported_range_high as number)}`)
    : MOCK_PROJECTION.supported_range;
  const improvement = (projection?.total_improvement_seconds as number) ?? MOCK_PROJECTION.total_improvement_seconds;
  const change21d = (projection?.twenty_one_day_change as number) ?? MOCK_PROJECTION.twenty_one_day_change;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SyncBanner />
      <ProjectionTile
        event={selectedEvent}
        projectedTime={projTime}
        range={projRange}
        improvementSeconds={improvement}
        twentyOneDayChange={change21d}
      />
      <EventSwiper
        apiData={null}
        selectedEvent={selectedEvent}
        onEventSelect={handleEventSelect}
      />
      <DriverStrip apiData={drivers} />
      <QuickMetrics readinessScore={readiness ? (readiness.score as number) : null} />
    </div>
  );
}
