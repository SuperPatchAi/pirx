"use client";

import { Card, CardContent } from "@/components/ui/card";

interface Metric {
  label: string;
  value: string;
  subtext?: string;
}

interface QuickMetricsProps {
  readinessScore?: number | null;
  sessionsPerWeek?: number | null;
  distanceKmPerWeek?: number | null;
  acwr?: number | null;
}

export function QuickMetrics({ readinessScore, sessionsPerWeek, distanceKmPerWeek, acwr }: QuickMetricsProps) {
  const metrics: Metric[] = [
    {
      label: "Sessions",
      value: sessionsPerWeek != null ? String(sessionsPerWeek) : "—",
      subtext: "this week",
    },
    {
      label: "Distance",
      value: distanceKmPerWeek != null ? `${Math.round(distanceKmPerWeek)}km` : "—",
      subtext: "this week",
    },
    {
      label: "ACWR",
      value: acwr != null ? acwr.toFixed(1) : "—",
      subtext: acwr != null ? (acwr >= 0.8 && acwr <= 1.3 ? "safe zone" : acwr > 1.5 ? "danger" : "caution") : "",
    },
    {
      label: "Readiness",
      value: readinessScore != null ? String(Math.round(readinessScore)) : "—",
      subtext: "/100",
    },
  ];
  return (
    <div className="grid grid-cols-4 gap-2">
      {metrics.map((m) => (
        <Card key={m.label}>
          <CardContent className="p-3 text-center space-y-0.5">
            <p className="text-[10px] text-muted-foreground">{m.label}</p>
            <p className="text-lg font-bold tabular-nums">{m.value}</p>
            {m.subtext && (
              <p className="text-[10px] text-muted-foreground">{m.subtext}</p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
