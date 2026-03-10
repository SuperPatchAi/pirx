"use client";

import { Card, CardContent } from "@/components/ui/card";

interface QuickMetricsProps {
  readinessScore?: number | null;
  sessionsPerWeek?: number | null;
  distanceKmPerWeek?: number | null;
  acwr?: number | null;
}

export function QuickMetrics({ readinessScore, sessionsPerWeek, distanceKmPerWeek, acwr }: QuickMetricsProps) {
  const metrics = [
    {
      label: "Sessions",
      value: sessionsPerWeek != null ? String(sessionsPerWeek) : "—",
      subtext: "this week",
      highlight: false,
    },
    {
      label: "Distance",
      value: distanceKmPerWeek != null ? `${Math.round(distanceKmPerWeek)}` : "—",
      unit: "km",
      subtext: "this week",
      highlight: true,
    },
    {
      label: "ACWR",
      value: acwr != null ? acwr.toFixed(1) : "—",
      subtext: acwr != null ? (acwr >= 0.8 && acwr <= 1.3 ? "safe zone" : acwr > 1.5 ? "danger" : "caution") : "",
      highlight: false,
    },
    {
      label: "Readiness",
      value: readinessScore != null ? String(Math.round(readinessScore)) : "—",
      subtext: "/100",
      highlight: true,
    },
  ];

  return (
    <div className="space-y-3">
      <h3 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
        Last 21 Days
      </h3>
      <div className="grid grid-cols-4 gap-2">
        {metrics.map((m) => (
          <Card key={m.label} className="border-border/40">
            <CardContent className="p-3 text-center space-y-0.5">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{m.label}</p>
              <p className={`text-xl font-bold tabular-nums ${m.highlight ? "text-green-500" : ""}`}>
                {m.value}
                {m.unit && <span className="text-xs font-normal text-muted-foreground ml-0.5">{m.unit}</span>}
              </p>
              {m.subtext && (
                <p className="text-[10px] text-muted-foreground/70">{m.subtext}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
