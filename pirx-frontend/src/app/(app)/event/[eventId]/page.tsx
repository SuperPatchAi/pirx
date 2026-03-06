"use client";

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
} from "lucide-react";
import Link from "next/link";
import { ProjectionHistoryChart } from "@/components/charts/projection-history-chart";

const EVENT_NAMES: Record<string, string> = {
  "1500": "1500m",
  "3000": "3K",
  "5000": "5K",
  "10000": "10K",
};

// TODO: Replace with API data
const MOCK_DATA: Record<
  string,
  {
    projected: string;
    range: string;
    baseline: string;
    improvement: number;
    change21d: number;
    drivers: {
      name: string;
      display: string;
      contribution: number;
      trend: string;
    }[];
    trajectory: { label: string; time: string; description: string; confidence?: number; delta?: number }[];
  }
> = {
  "1500": {
    projected: "5:42",
    range: "5:35 – 5:48",
    baseline: "5:55",
    improvement: 13,
    change21d: 3,
    drivers: [
      {
        name: "aerobic_base",
        display: "Aerobic Base",
        contribution: 3.9,
        trend: "improving",
      },
      {
        name: "threshold_density",
        display: "Threshold",
        contribution: 3.3,
        trend: "improving",
      },
      {
        name: "speed_exposure",
        display: "Speed",
        contribution: 2.0,
        trend: "stable",
      },
      {
        name: "running_economy",
        display: "Economy",
        contribution: 2.0,
        trend: "stable",
      },
      {
        name: "load_consistency",
        display: "Consistency",
        contribution: 1.8,
        trend: "improving",
      },
    ],
    trajectory: [
      { label: "Maintain", time: "5:40", description: "Continue current pattern", confidence: 0.85, delta: 2 },
      { label: "Push", time: "5:36", description: "Increase threshold & speed work", confidence: 0.65, delta: 6 },
      { label: "Ease off", time: "5:46", description: "Reduce volume, maintain quality", confidence: 0.75, delta: -4 },
    ],
  },
  "5000": {
    projected: "19:42",
    range: "19:15 – 20:08",
    baseline: "21:00",
    improvement: 78,
    change21d: 5,
    drivers: [
      {
        name: "aerobic_base",
        display: "Aerobic Base",
        contribution: 23.4,
        trend: "improving",
      },
      {
        name: "threshold_density",
        display: "Threshold",
        contribution: 19.5,
        trend: "improving",
      },
      {
        name: "speed_exposure",
        display: "Speed",
        contribution: 11.7,
        trend: "stable",
      },
      {
        name: "running_economy",
        display: "Economy",
        contribution: 12.2,
        trend: "stable",
      },
      {
        name: "load_consistency",
        display: "Consistency",
        contribution: 11.2,
        trend: "improving",
      },
    ],
    trajectory: [
      { label: "Maintain", time: "19:39", description: "Continue current pattern", confidence: 0.85, delta: 3 },
      { label: "Push", time: "19:34", description: "Increase threshold & speed work", confidence: 0.65, delta: 8 },
      { label: "Ease off", time: "19:47", description: "Reduce volume, maintain quality", confidence: 0.75, delta: -5 },
    ],
  },
};

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
  const data = MOCK_DATA[eventId] || MOCK_DATA["5000"];
  const eventName = EVENT_NAMES[eventId] || eventId;

  // TODO: Replace with API data
  const baselineParts = data.baseline.split(":");
  const baselineSeconds =
    parseFloat(baselineParts[0]) * 60 +
    parseFloat(baselineParts[1] || "0");
  const mockHistory = Array.from({ length: 30 }, (_, i) => {
    const date = new Date(2026, 2, 5);
    date.setDate(date.getDate() - (29 - i));
    return {
      date: date.toISOString().split("T")[0],
      time: baselineSeconds - i * (data.improvement / 30),
    };
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
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
            data={mockHistory}
            baselineTime={baselineSeconds}
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
        {data.trajectory.map((t) => (
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
