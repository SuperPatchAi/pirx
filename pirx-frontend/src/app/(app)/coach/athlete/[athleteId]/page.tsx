"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  ChevronLeft,
  Loader2,
  TrendingDown,
  TrendingUp,
  Minus,
  Timer,
  Activity,
  Heart,
} from "lucide-react";

const EVENT_NAMES: Record<string, string> = {
  "1500": "1500m",
  "3000": "3K",
  "5000": "5K",
  "10000": "10K",
  "21097": "Half Marathon",
  "42195": "Marathon",
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

interface Projection {
  projected_time: string;
  projected_time_seconds: number;
  range_low: number | null;
  range_high: number | null;
  twenty_one_day_change: number;
}

interface Driver {
  name: string;
  display_name: string;
  contribution_seconds: number;
  score: number;
  trend: string;
}

interface Readiness {
  score: number;
  label: string;
  factors: string[];
}

const trendConfig: Record<string, { icon: typeof TrendingUp; color: string }> = {
  improving: { icon: TrendingUp, color: "text-primary" },
  declining: { icon: TrendingDown, color: "text-destructive" },
  stable: { icon: Minus, color: "text-muted-foreground" },
};

export default function AthleteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const athleteId = params.athleteId as string;

  const [loading, setLoading] = useState(true);
  const [primaryEvent, setPrimaryEvent] = useState("5000");
  const [projections, setProjections] = useState<Record<string, Projection>>({});
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [readiness, setReadiness] = useState<Readiness | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const { apiFetch } = await import("@/lib/api");
        const [projResult, driversResult, readinessResult] = await Promise.allSettled([
          apiFetch(`/coach/athlete/${athleteId}/projection`),
          apiFetch(`/coach/athlete/${athleteId}/drivers`),
          apiFetch(`/coach/athlete/${athleteId}/readiness`),
        ]);

        if (projResult.status === "fulfilled") {
          setPrimaryEvent(projResult.value.primary_event ?? "5000");
          setProjections(projResult.value.projections ?? {});
        }
        if (driversResult.status === "fulfilled") {
          setDrivers(driversResult.value.drivers ?? []);
        }
        if (readinessResult.status === "fulfilled") {
          setReadiness(readinessResult.value);
        }
      } catch {
        // fallback — empty state
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [athleteId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const eventOrder = ["1500", "3000", "5000", "10000", "21097", "42195"];
  const maxDriverScore = Math.max(...drivers.map((d) => d.score), 1);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => router.push("/coach")}>
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">Athlete Detail</h1>
      </div>

      {/* Projections Table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Timer className="h-4 w-4" />
            Projections
          </CardTitle>
        </CardHeader>
        <CardContent>
          {Object.keys(projections).length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">
              No projection data available yet.
            </p>
          ) : (
            <div className="space-y-2">
              {eventOrder.map((ev) => {
                const proj = projections[ev];
                if (!proj) return null;
                const isPrimary = ev === primaryEvent;
                const change = proj.twenty_one_day_change ?? 0;
                const TrendIcon =
                  change > 0
                    ? TrendingDown
                    : change < 0
                      ? TrendingUp
                      : Minus;
                const trendColor =
                  change > 0
                    ? "text-primary"
                    : change < 0
                      ? "text-destructive"
                      : "text-muted-foreground";

                return (
                  <div
                    key={ev}
                    className={`flex items-center justify-between rounded-lg border p-3 ${isPrimary ? "border-primary/50 bg-primary/5" : ""}`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium w-24">
                        {EVENT_NAMES[ev]}
                      </span>
                      {isPrimary && (
                        <Badge variant="secondary" className="text-[10px]">
                          Primary
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4">
                      {proj.range_low != null && proj.range_high != null && (
                        <span className="text-xs text-muted-foreground hidden sm:inline">
                          {formatTime(proj.range_low)} – {formatTime(proj.range_high)}
                        </span>
                      )}
                      <span className="text-sm font-bold tabular-nums w-20 text-right">
                        {proj.projected_time}
                      </span>
                      <div className="flex items-center gap-1 w-16 justify-end">
                        <TrendIcon className={`h-3.5 w-3.5 ${trendColor}`} />
                        <span className={`text-xs tabular-nums ${trendColor}`}>
                          {change > 0 ? "-" : "+"}
                          {Math.abs(change)}s
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Driver Breakdown */}
      {drivers.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Driver Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {drivers.map((d) => {
              const { icon: TrendIcon, color } =
                trendConfig[d.trend] || trendConfig.stable;
              const pct = maxDriverScore > 0 ? (d.score / maxDriverScore) * 100 : 0;
              return (
                <div key={d.name} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {d.display_name}
                      </span>
                      <TrendIcon className={`h-3.5 w-3.5 ${color}`} />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {d.score}/100
                      </span>
                      <span
                        className={`text-sm font-bold tabular-nums ${d.contribution_seconds < 0 ? "text-primary" : d.contribution_seconds > 0 ? "text-destructive" : "text-muted-foreground"}`}
                      >
                        {d.contribution_seconds < 0 ? "" : "+"}
                        {d.contribution_seconds}s
                      </span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      <Separator />

      {/* Readiness */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Heart className="h-4 w-4" />
            Event Readiness
          </CardTitle>
        </CardHeader>
        <CardContent>
          {readiness ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-3xl font-bold tabular-nums">
                  {readiness.score}
                  <span className="text-lg text-muted-foreground">/100</span>
                </span>
                <Badge
                  variant={
                    readiness.score >= 70
                      ? "default"
                      : readiness.score >= 40
                        ? "secondary"
                        : "destructive"
                  }
                >
                  {readiness.label}
                </Badge>
              </div>
              {readiness.factors.length > 0 && (
                <div className="space-y-1">
                  {readiness.factors.map((f, i) => (
                    <p key={i} className="text-xs text-muted-foreground">
                      {f}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-4">
              Readiness data not available.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
