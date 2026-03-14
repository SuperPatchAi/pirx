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
  aerobic_base: "bg-[#2eb8a1]",
  threshold: "bg-primary",
  speed: "bg-destructive",
  load: "bg-[#5f665c]",
  economy: "bg-destructive",
};

const TREND_LABELS: Record<string, { label: string; className: string }> = {
  improving: { label: "Confirmed", className: "text-primary" },
  stable: { label: "Observational", className: "text-muted-foreground" },
  declining: { label: "Emerging", className: "text-[#dc9518]" },
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
    <Card className="border-border card-hover">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Driver Seconds
            </h3>
            <p className="text-xs font-body text-muted-foreground mt-0.5">
              Where time is gained and lost
            </p>
          </div>
          <div className="text-right">
            <p className={`font-display text-5xl tabular-nums tracking-wide ${netSeconds < 0 ? "text-primary" : "text-destructive"}`}>
              {netSeconds < 0 ? "" : "+"}{netSeconds.toFixed(0)}s
            </p>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Net Gained</p>
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
                  <span className="text-xs font-medium text-foreground">{d.displayName}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] ${trend.className}`}>{trend.label}</span>
                    <span className={`font-mono-data text-[13px] font-bold tabular-nums ${cs < 0 ? "text-primary" : cs > 0 ? "text-destructive" : "text-muted-foreground"}`}>
                      {cs < 0 ? "" : "+"}{cs.toFixed(1)}s
                    </span>
                  </div>
                </div>
                <div className="h-5 w-full rounded-xl bg-[#232522] overflow-hidden shadow-[inset_0px_1px_3px_0px_rgba(10,11,9,0.4)]">
                  <div
                    className={`h-full rounded-xl ${barColor} transition-all duration-500`}
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
