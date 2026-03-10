"use client";

import { useState, useEffect, useCallback } from "react";
import { ProjectionTile } from "@/components/home/projection-tile";
import { EventSwiper } from "@/components/home/event-swiper";
import { DriverStrip, type DriverApiItem } from "@/components/home/driver-strip";
import { QuickMetrics } from "@/components/home/quick-metrics";
import { SyncBanner } from "@/components/home/sync-banner";
import { useProjectionRealtime } from "@/hooks/use-projection-realtime";
import { useProjectionStore } from "@/stores/projection-store";
import { useTourStore } from "@/stores/tour-store";
import { useAuth } from "@/hooks/use-auth";
import { ShareModal, type CardData } from "@/components/social/share-modal";
import { Loader2, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const EMPTY_PROJECTION = {
  projected_time: "—",
  supported_range: "—",
  total_improvement_seconds: 0,
  twenty_one_day_change: 0,
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

const EVENT_LABELS: Record<string, string> = {
  "1500": "1500m",
  "3000": "3K",
  "5000": "5K",
  "10000": "10K",
  "21097": "Half Marathon",
  "42195": "Marathon",
};

function formatEventLabel(event: string): string {
  return EVENT_LABELS[event] ?? `${event}m`;
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [projection, setProjection] = useState<Record<string, unknown> | null>(null);
  const [allEvents, setAllEvents] = useState<{ event: string; displayName: string; projectedTime: string; change: string }[] | null>(null);
  const [drivers, setDrivers] = useState<DriverApiItem[] | null>(null);
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [metrics, setMetrics] = useState<{ sessions: number | null; distanceKm: number | null; acwr: number | null }>({ sessions: null, distanceKm: null, acwr: null });
  const [syncStatus, setSyncStatus] = useState<{ lastSync: string | null; syncing: boolean }>({ lastSync: null, syncing: false });
  const [selectedEvent, setSelectedEvent] = useState("5000");
  const [shareOpen, setShareOpen] = useState(false);
  const [cardData, setCardData] = useState<CardData | null>(null);
  const [cohortPercentile, setCohortPercentile] = useState<number | null>(null);

  const { user } = useAuth();
  useProjectionRealtime(user?.id ?? null);

  const { startTour, hasCompleted, isActive: tourActive } = useTourStore();

  useEffect(() => {
    if (!loading && !tourActive && !hasCompleted()) {
      const timer = setTimeout(() => startTour(), 600);
      return () => clearTimeout(timer);
    }
  }, [loading]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const storeSetCurrentEvent = useProjectionStore((s) => s.setCurrentEvent);

  const handleEventSelect = useCallback(
    (event: string) => {
      setSelectedEvent(event);
      storeSetCurrentEvent(event);
      fetchProjection(event);
    },
    [fetchProjection, storeSetCurrentEvent]
  );

  const loadDashboardData = useCallback(async () => {
    try {
      const { apiFetch } = await import("@/lib/api");
      const [projData, driversData, readinessData, allEventsData, weeklyData, syncData] = await Promise.allSettled([
        apiFetch(`/projection?event=${selectedEvent}`),
        apiFetch("/drivers"),
        apiFetch("/readiness"),
        apiFetch("/projection/all"),
        apiFetch("/metrics/weekly"),
        apiFetch("/sync/status"),
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
      if (allEventsData.status === "fulfilled") {
        const evts = allEventsData.value as { projections?: Array<{ event?: string; display_name?: string; projected_time_seconds?: number; twenty_one_day_change?: number }> };
        const list = evts?.projections ?? (Array.isArray(allEventsData.value) ? allEventsData.value as Array<{ event?: string; display_name?: string; projected_time_seconds?: number; twenty_one_day_change?: number }> : []);
        if (list.length > 0) {
          setAllEvents(
            list.map((p) => ({
              event: String(p.event ?? ""),
              displayName: p.display_name ?? formatEventLabel(String(p.event ?? "")),
              projectedTime: formatTime(p.projected_time_seconds ?? 0),
              change: p.twenty_one_day_change != null ? `${p.twenty_one_day_change > 0 ? "+" : ""}${p.twenty_one_day_change}s` : "—",
            }))
          );
        }
      }
      if (weeklyData.status === "fulfilled") {
        const w = weeklyData.value as { sessions_per_week?: number; distance_km_per_week?: number; acwr?: number };
        setMetrics({
          sessions: w.sessions_per_week ?? null,
          distanceKm: w.distance_km_per_week ?? null,
          acwr: w.acwr ?? null,
        });
      }
      if (syncData.status === "fulfilled") {
        const s = syncData.value as { connections?: Array<{ last_sync?: string }> };
        const latest = s.connections?.map(c => c.last_sync).filter(Boolean).sort().pop() ?? null;
        setSyncStatus((prev) => ({ ...prev, lastSync: latest }));
      }
    } catch {
      // keep existing data on failure
    }
  }, [selectedEvent]);

  useEffect(() => {
    loadDashboardData().finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSyncNow = useCallback(async () => {
    setSyncStatus((prev) => ({ ...prev, syncing: true }));
    try {
      const { apiFetch } = await import("@/lib/api");
      await apiFetch("/sync/trigger", { method: "POST" });
      await apiFetch("/sync/recompute", { method: "POST" });
      await loadDashboardData();
      setSyncStatus((prev) => ({ ...prev, syncing: false }));
    } catch {
      setSyncStatus((prev) => ({ ...prev, syncing: false }));
    }
  }, [loadDashboardData]);

  const handleShare = useCallback(async () => {
    try {
      const { apiFetch } = await import("@/lib/api");
      const [cardRes, cohortRes] = await Promise.allSettled([
        apiFetch(`/social/card-data?event=${selectedEvent}`),
        apiFetch(`/social/cohort?event=${selectedEvent}`),
      ]);
      if (cardRes.status === "fulfilled") {
        setCardData(cardRes.value as CardData);
      }
      if (cohortRes.status === "fulfilled") {
        const c = cohortRes.value as { percentile?: number | null };
        setCohortPercentile(c.percentile ?? null);
      }
      setShareOpen(true);
    } catch {
      // Failed to load share data
    }
  }, [selectedEvent]);

  const projTime = projection
    ? (projection.projected_time_display as string) ?? formatTime(projection.projected_time_seconds as number)
    : EMPTY_PROJECTION.projected_time;
  const projRange = projection
    ? ((projection.supported_range_display as string) ?? `${formatTime(projection.supported_range_low as number)} – ${formatTime(projection.supported_range_high as number)}`)
    : EMPTY_PROJECTION.supported_range;
  const improvement = (projection?.total_improvement_seconds as number) ?? EMPTY_PROJECTION.total_improvement_seconds;
  const change21d = (projection?.twenty_one_day_change as number) ?? EMPTY_PROJECTION.twenty_one_day_change;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SyncBanner lastSync={syncStatus.lastSync} syncing={syncStatus.syncing} onSyncNow={handleSyncNow} />

      <div data-tour="projection-tile" className="relative">
        <ProjectionTile
          event={selectedEvent}
          projectedTime={projTime}
          range={projRange}
          improvementSeconds={improvement}
          twentyOneDayChange={change21d}
        />
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-3 right-3 text-muted-foreground hover:text-foreground"
          onClick={handleShare}
          aria-label="Share projection"
        >
          <Share2 className="h-4 w-4" />
        </Button>
      </div>

      <div data-tour="event-swiper">
        <EventSwiper
          apiData={allEvents}
          selectedEvent={selectedEvent}
          onEventSelect={handleEventSelect}
        />
      </div>

      <div data-tour="driver-strip">
        <DriverStrip apiData={drivers} />
      </div>

      <QuickMetrics
        readinessScore={readiness ? (readiness.score as number) : null}
        sessionsPerWeek={metrics.sessions}
        distanceKmPerWeek={metrics.distanceKm}
        acwr={metrics.acwr}
      />

      <ShareModal
        open={shareOpen}
        onOpenChange={setShareOpen}
        cardData={cardData}
        percentile={cohortPercentile}
      />
    </div>
  );
}
