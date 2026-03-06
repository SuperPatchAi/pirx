"use client";

import { Card, CardContent } from "@/components/ui/card";

interface Metric {
  label: string;
  value: string;
  subtext?: string;
}

const MOCK_METRICS: Metric[] = [
  { label: "Sessions", value: "5", subtext: "this week" },
  { label: "Distance", value: "42km", subtext: "this week" },
  { label: "ACWR", value: "1.1", subtext: "safe zone" },
  { label: "Readiness", value: "82", subtext: "/100" },
];

export function QuickMetrics() {
  return (
    <div className="grid grid-cols-4 gap-2">
      {MOCK_METRICS.map((m) => (
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
