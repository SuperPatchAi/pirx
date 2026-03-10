"use client";

import { EmptyState } from "@/components/ui/empty-state";
import { Card, CardContent } from "@/components/ui/card";
import { BarChart3 } from "lucide-react";

export interface DriverApiItem {
  name: string;
  displayName: string;
  contributionSeconds: number;
  trend: "improving" | "stable" | "declining";
  score: number;
}

interface DriverStripProps {
  apiData?: DriverApiItem[] | null;
}

const DRIVER_COLORS: Record<string, string> = {
  aerobic_base: "bg-green-500",
  threshold: "bg-yellow-400",
  speed: "bg-red-400",
  load: "bg-orange-400",
  economy: "bg-cyan-400",
};

const TREND_LABELS: Record<string, { label: string; className: string }> = {
  improving: { label: "Confirmed", className: "text-green-500" },
  stable: { label: "Observational", className: "text-muted-foreground" },
  declining: { label: "Emerging", className: "text-orange-400" },
};

export function DriverStrip({ apiData }: DriverStripProps) {
  const drivers = apiData ?? [];

  if (drivers.length === 0) {
    return (
      <div className="space-y-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
          Driver Seconds
        </h3>
        <EmptyState
          icon={BarChart3}
          message="No driver data yet"
          submessage="Sync data to see what's driving your improvement"
        />
      </div>
    );
  }

  const totalAbs = drivers.reduce((sum, d) => sum + Math.abs(d.contributionSeconds), 0) || 1;
  const netSeconds = drivers.reduce((sum, d) => sum + d.contributionSeconds, 0);

  return (
    <Card className="border-border/40 card-hover">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Driver Seconds
            </h3>
            <p className="text-[10px] text-muted-foreground/70 mt-0.5">
              Where time is gained and lost
            </p>
          </div>
          <div className="text-right">
            <p className={`text-2xl font-bold tabular-nums ${netSeconds < 0 ? "text-green-500" : "text-red-400"}`}>
              {netSeconds < 0 ? "" : "+"}{netSeconds.toFixed(0)}s
            </p>
            <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wide">Net Gained</p>
          </div>
        </div>

        <div className="space-y-3">
          {drivers.map((d) => {
            const cs = d.contributionSeconds;
            const barWidth = Math.min((Math.abs(cs) / totalAbs) * 100, 100);
            const barColor = DRIVER_COLORS[d.name] ?? "bg-muted-foreground";
            const trend = TREND_LABELS[d.trend] ?? TREND_LABELS.stable;

            return (
              <div key={d.name} className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{d.displayName}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] ${trend.className}`}>{trend.label}</span>
                    <span className={`text-sm font-semibold tabular-nums ${cs < 0 ? "text-green-500" : cs > 0 ? "text-red-400" : "text-muted-foreground"}`}>
                      {cs < 0 ? "" : "+"}{cs.toFixed(1)}s
                    </span>
                  </div>
                </div>
                <div className="h-2 w-full rounded-full bg-secondary/50 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${barColor} transition-all duration-500`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
