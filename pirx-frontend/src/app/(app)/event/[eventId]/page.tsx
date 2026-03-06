"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { motion } from "framer-motion";
import {
  ChevronLeft,
  Timer,
  TrendingDown,
  TrendingUp,
  Minus,
  Target,
  BarChart3,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { ProjectionHistoryChart } from "@/components/charts/projection-history-chart";

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

const EVENT_NAMES: Record<string, string> = {
  "1500": "1500m",
  "3000": "3K",
  "5000": "5K",
  "10000": "10K",
};

const EMPTY_DRIVERS: { name: string; display: string; contribution: number; trend: string }[] = [];
const EMPTY_TRAJECTORY: { label: string; time: string; description: string; confidence?: number; delta?: number }[] = [];

const trendConfig: Record<
  string,
  { icon: typeof TrendingUp; color: string }
> = {
  improving: { icon: TrendingDown, color: "text-green-500" },
  stable: { icon: Minus, color: "text-muted-foreground" },
  declining: { icon: TrendingUp, color: "text-red-500" },
};

export default function EventPage() {
  const router = useRouter();
  const params = useParams();
  const eventId = params.eventId as string;
  const eventName = EVENT_NAMES[eventId] || eventId;

  const [loading, setLoading] = useState(true);
  const [projection, setProjection] = useState<{
    projected: string;
    range: string;
    baseline: string;
    improvement: number;
    change21d: number;
  } | null>(null);
  const [historyData, setHistoryData] = useState<{ date: string; time: number }[] | null>(null);
  const [trajectoryData, setTrajectoryData] = useState<
    { label: string; time: string; description: string; confidence?: number; delta?: number }[]
  | null>(null);
  const [rangeData, setRangeData] = useState<{ date: string; low: number; high: number }[] | null>(null);
  const [driversData, setDriversData] = useState<
    { name: string; display: string; contribution: number; trend: string }[] | null
  >(null);

  useEffect(() => {
    async function load() {
      try {
        const { apiFetch } = await import("@/lib/api");
        const [proj, history, trajectory, drivers] = await Promise.allSettled([
          apiFetch(`/projection?event=${eventId}`),
          apiFetch(`/projection/history?event=${eventId}&days=30`),
          apiFetch(`/projection/trajectory?event=${eventId}`),
          apiFetch(`/drivers`),
        ]);

        if (proj.status === "fulfilled") {
          const p = proj.value as {
            projected_time?: string;
            projected_time_seconds?: number;
            supported_range?: string;
            supported_range_low?: number;
            supported_range_high?: number;
            total_improvement_seconds?: number;
            twenty_one_day_change?: number;
          };
          const projSeconds = p.projected_time_seconds ?? 0;
          const improvement = p.total_improvement_seconds ?? 0;
          const baselineSeconds = projSeconds + improvement;
          setProjection({
            projected: p.projected_time ?? formatTime(projSeconds),
            range:
              p.supported_range ??
              (p.supported_range_low != null && p.supported_range_high != null
                ? `${formatTime(p.supported_range_low)} – ${formatTime(p.supported_range_high)}`
                : "—"),
            baseline: formatTime(baselineSeconds),
            improvement,
            change21d: p.twenty_one_day_change ?? 0,
          });
        }

        if (history.status === "fulfilled") {
          const h = history.value as {
            history?: Array<{
              date: string;
              projected_time_seconds?: number;
              range_low?: number;
              range_high?: number;
            }>;
            points?: Array<{
              date: string;
              projected_time_seconds?: number;
              range_low?: number;
              range_high?: number;
            }>;
          };
          const points = h.history ?? h.points ?? [];
          setHistoryData(
            points.map((pt) => ({
              date: pt.date,
              time: pt.projected_time_seconds ?? 0,
            }))
          );
          const ranges = points
            .filter((pt) => pt.range_low != null && pt.range_high != null)
            .map((pt) => ({
              date: pt.date,
              low: pt.range_low!,
              high: pt.range_high!,
            }));
          if (ranges.length > 0) setRangeData(ranges);
        }

        if (trajectory.status === "fulfilled") {
          const t = trajectory.value as {
            scenarios?: Array<{
              label: string;
              projected_time?: string;
              delta_seconds?: number;
              description?: string;
              confidence?: number;
            }>;
          };
          const scenarios = t.scenarios ?? [];
          setTrajectoryData(
            scenarios.map((s) => ({
              label: s.label,
              time: s.projected_time ?? "",
              description: s.description ?? "",
              confidence: s.confidence,
              delta: s.delta_seconds,
            }))
          );
        }

        if (drivers.status === "fulfilled") {
          const driverNames: Record<string, string> = {
            aerobic_base: "Aerobic Base",
            threshold_density: "Threshold",
            speed_exposure: "Speed",
            running_economy: "Economy",
            load_consistency: "Consistency",
          };
          const d = drivers.value as {
            drivers?: Array<{
              name?: string;
              contribution_seconds?: number;
              trend?: string;
              score?: number;
            }>;
          } | Array<{
            name?: string;
            contribution_seconds?: number;
            trend?: string;
            score?: number;
          }>;
          const list = Array.isArray(d) ? d : (d.drivers ?? []);
          if (list.length > 0) {
            setDriversData(
              list.map((dr) => ({
                name: dr.name ?? "",
                display: driverNames[dr.name ?? ""] ?? dr.name ?? "",
                contribution: dr.contribution_seconds ?? 0,
                trend: dr.trend ?? "stable",
              }))
            );
          }
        }
      } catch {
        // Use mock on failure
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [eventId]);

  const data = {
    projected: projection?.projected ?? "—",
    range: projection?.range ?? "—",
    baseline: projection?.baseline ?? "—",
    improvement: projection?.improvement ?? 0,
    change21d: projection?.change21d ?? 0,
    drivers: driversData ?? EMPTY_DRIVERS,
    trajectory: trajectoryData ?? EMPTY_TRAJECTORY,
  };

  const baselineParts = data.baseline.includes(":") ? data.baseline.split(":") : [];
  const baselineSeconds =
    baselineParts.length >= 2
      ? parseFloat(baselineParts[0]) * 60 + parseFloat(baselineParts[1] || "0")
      : 0;
  const chartData =
    historyData ??
    Array.from({ length: 30 }, (_, i) => {
      const date = new Date(2026, 2, 5);
      date.setDate(date.getDate() - (29 - i));
      return {
        date: date.toISOString().split("T")[0],
        time: baselineSeconds - i * (data.improvement / 30),
      };
    });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" aria-label="Go back" onClick={() => router.back()}>
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{eventName}</h1>
          <p className="text-sm text-muted-foreground">Event Projection</p>
        </div>
      </div>

      {/* Projection Hero */}
      <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
        <CardContent className="p-6 space-y-3">
          <div className="flex items-center gap-2">
            <Timer className="h-4 w-4 text-primary" />
            <span className="text-sm text-muted-foreground">Projected Time</span>
          </div>
          <p className="text-5xl font-bold tabular-nums tracking-tight">
            {data.projected}
          </p>
          <p className="text-sm text-muted-foreground">
            Supported Range: {data.range}
          </p>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <TrendingDown className="h-3.5 w-3.5 text-green-500" />
              <span className="text-sm font-medium text-green-500">
                -{data.improvement}s total
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-sm font-medium text-green-500">
                -{data.change21d}s
              </span>
              <span className="text-xs text-muted-foreground">21-day</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Baseline: {data.baseline} ({eventName})
          </p>
        </CardContent>
      </Card>

      {/* Projection History Chart Placeholder */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Projection History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ProjectionHistoryChart
            data={chartData}
            baselineTime={baselineSeconds}
            rangeData={rangeData ?? undefined}
          />
        </CardContent>
      </Card>

      {/* Driver Breakdown */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground">
          Driver Contributions
        </h3>
        {data.drivers.map((d) => {
          const { icon: TrendIcon, color } =
            trendConfig[d.trend] || trendConfig.stable;
          const pct =
            data.improvement > 0
              ? (d.contribution / data.improvement) * 100
              : 0;
          return (
            <Link key={d.name} href={`/driver/${d.name}`}>
              <Card className="hover:border-primary/50 transition-colors mb-2">
                <CardContent className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{d.display}</span>
                      <TrendIcon className={`h-3.5 w-3.5 ${color}`} />
                    </div>
                    <span className="text-sm font-bold tabular-nums">
                      -{d.contribution}s
                    </span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      <Separator />

      {/* 2-Week Trajectory */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          <Target className="h-4 w-4" />
          2-Week Trajectory
        </h3>
        {(data.trajectory ?? []).map((t) => (
          <Card key={t.label}>
            <CardContent className="flex items-center justify-between p-3">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium">{t.label}</p>
                  {t.confidence != null && (
                    <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                      {Math.round(t.confidence * 100)}% confidence
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">{t.description}</p>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold tabular-nums">{t.time}</p>
                {t.delta !== undefined && t.delta !== 0 && (
                  <p className={`text-xs ${t.delta > 0 ? "text-green-500" : "text-red-500"}`}>
                    {t.delta > 0 ? "-" : "+"}{Math.abs(t.delta)}s
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </motion.div>
  );
}
