"use client";

import { useState, useEffect, useCallback } from "react";
import { ProjectionTile } from "@/components/home/projection-tile";
import { EventSwiper } from "@/components/home/event-swiper";
import { DriverStrip, type DriverApiItem } from "@/components/home/driver-strip";
import { QuickMetrics } from "@/components/home/quick-metrics";
import { SyncBanner } from "@/components/home/sync-banner";
import { ReadinessRing } from "@/components/home/readiness-ring";
import { WeeklyVolumeChart } from "@/components/home/weekly-volume-chart";
import { HrSparkline } from "@/components/home/hr-sparkline";
import { AnimatedSection } from "@/components/ui/animated-section";
import { DashboardSkeleton } from "@/components/ui/skeleton-card";
import { useProjectionRealtime } from "@/hooks/use-projection-realtime";
import { useProjectionStore } from "@/stores/projection-store";
import { useTourStore } from "@/stores/tour-store";
import { useAuth } from "@/hooks/use-auth";
import { ShareModal, type CardData } from "@/components/social/share-modal";
import { Share2 } from "lucide-react";
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

function getProjectedTimeLabel(p: {
  projected_time_seconds?: number | string | null;
  midpoint_seconds?: number | string | null;
  projected_time_display?: string | null;
}): string {
  if (typeof p.projected_time_display === "string" && p.projected_time_display.trim()) {
    return p.projected_time_display;
  }
  const rawSeconds = p.projected_time_seconds ?? p.midpoint_seconds;
  const seconds =
    typeof rawSeconds === "number"
      ? rawSeconds
      : typeof rawSeconds === "string"
        ? Number(rawSeconds)
        : NaN;
  return Number.isFinite(seconds) ? formatTime(seconds) : "—";
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
  const [weeklyVolume, setWeeklyVolume] = useState<{ days: { day: string; easy: number; tempo: number; long: number }[]; total_km: number } | null>(null);
  const [hrTrend, setHrTrend] = useState<{ points: { date: string; avg_hr: number }[]; avg: number | null; max: number | null } | null>(null);
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
      const [projData, driversData, readinessData, allEventsData, weeklyData, syncData, volumeData, hrData] = await Promise.allSettled([
        apiFetch(`/projection?event=${selectedEvent}`),
        apiFetch("/drivers"),
        apiFetch("/readiness"),
        apiFetch("/projection/all"),
        apiFetch("/metrics/weekly"),
        apiFetch("/sync/status"),
        apiFetch("/features/weekly-volume"),
        apiFetch("/features/hr-trend"),
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
        const evts = allEventsData.value as {
          projections?: Array<{
            event?: string;
            display_name?: string;
            projected_time_seconds?: number | string;
            midpoint_seconds?: number | string;
            projected_time_display?: string;
            twenty_one_day_change?: number | string;
          }>;
        };
        const list = evts?.projections ?? (
          Array.isArray(allEventsData.value)
            ? (allEventsData.value as Array<{
                event?: string;
                display_name?: string;
                projected_time_seconds?: number | string;
                midpoint_seconds?: number | string;
                projected_time_display?: string;
                twenty_one_day_change?: number | string;
              }>)
            : []
        );
        if (list.length > 0) {
          setAllEvents(
            list.map((p) => ({
              event: String(p.event ?? ""),
              displayName: p.display_name ?? formatEventLabel(String(p.event ?? "")),
              projectedTime: getProjectedTimeLabel(p),
              change:
                p.twenty_one_day_change != null
                  ? `${Number(p.twenty_one_day_change) > 0 ? "+" : ""}${Number(p.twenty_one_day_change)}s`
                  : "—",
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
      if (volumeData.status === "fulfilled") {
        setWeeklyVolume(volumeData.value as { days: { day: string; easy: number; tempo: number; long: number }[]; total_km: number });
      }
      if (hrData.status === "fulfilled") {
        setHrTrend(hrData.value as { points: { date: string; avg_hr: number }[]; avg: number | null; max: number | null });
      }
    } catch {
      // keep existing data on failure
    }
  }, [selectedEvent]);

  useEffect(() => {
    let cancelled = false;
    loadDashboardData().finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
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
  const modelSource = (projection?.model_source as string | undefined) ?? null;
  const modelConfidence = (projection?.model_confidence as number | undefined) ?? null;
  const fallbackReason = (projection?.fallback_reason as string | undefined) ?? null;

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6">
      <AnimatedSection delay={0}>
        <SyncBanner lastSync={syncStatus.lastSync} syncing={syncStatus.syncing} onSyncNow={handleSyncNow} />
      </AnimatedSection>

      <AnimatedSection delay={0.05}>
        <div data-tour="projection-tile" className="relative">
          <ProjectionTile
            event={selectedEvent}
            projectedTime={projTime}
            range={projRange}
            improvementSeconds={improvement}
            twentyOneDayChange={change21d}
            modelSource={modelSource}
            modelConfidence={modelConfidence}
            fallbackReason={fallbackReason}
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
      </AnimatedSection>

      <AnimatedSection delay={0.1}>
        <div data-tour="event-swiper">
          <EventSwiper
            apiData={allEvents}
            selectedEvent={selectedEvent}
            onEventSelect={handleEventSelect}
          />
        </div>
      </AnimatedSection>

      <AnimatedSection delay={0.15}>
        <div data-tour="driver-strip">
          <DriverStrip apiData={drivers} />
        </div>
      </AnimatedSection>

      <AnimatedSection delay={0.2}>
        <WeeklyVolumeChart
          data={weeklyVolume?.days ?? null}
          totalKm={weeklyVolume?.total_km ?? null}
        />
      </AnimatedSection>

      <AnimatedSection delay={0.25}>
        <QuickMetrics
          readinessScore={readiness ? (readiness.score as number) : null}
          sessionsPerWeek={metrics.sessions}
          distanceKmPerWeek={metrics.distanceKm}
          acwr={metrics.acwr}
        />
      </AnimatedSection>

      <AnimatedSection delay={0.28}>
        <ReadinessRing
          score={readiness ? (readiness.score as number) : null}
          staminaPct={readiness ? Math.round(((readiness.score as number) ?? 0) * 0.74) : null}
        />
      </AnimatedSection>

      <AnimatedSection delay={0.3}>
        <HrSparkline
          data={hrTrend?.points ?? null}
          avg={hrTrend?.avg ?? null}
          max={hrTrend?.max ?? null}
        />
      </AnimatedSection>

      <ShareModal
        open={shareOpen}
        onOpenChange={setShareOpen}
        cardData={cardData}
        percentile={cohortPercentile}
      />
    </div>
  );
}
