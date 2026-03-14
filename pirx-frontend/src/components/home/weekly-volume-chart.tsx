"use client";

import {
  BarChart,
  Bar,
  XAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, CardContent } from "@/components/ui/card";

const EASY_COLOR = "#4b5049";
const TEMPO_COLOR = "#0faaea";
const LONG_COLOR = "#dc9518";

export interface WeeklyVolumeChartProps {
  data: { day: string; easy: number; tempo: number; long: number }[] | null;
  totalKm: number | null;
}

function NoData() {
  return (
    <div className="h-[180px] flex items-center justify-center text-sm text-muted-foreground">
      No data yet
    </div>
  );
}

const tooltipStyle = {
  backgroundColor: "#1e201d",
  border: "1px solid #2b2d2a",
  borderRadius: "14px",
  fontSize: "12px",
  padding: "8px 12px",
};

export function WeeklyVolumeChart({ data, totalKm }: WeeklyVolumeChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card className="border-border">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[11px] uppercase tracking-[0.18em] font-medium text-muted-foreground">
              This Week
            </h3>
          </div>
          <NoData />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[11px] uppercase tracking-[0.18em] font-medium text-muted-foreground">
            This Week
          </h3>
          {totalKm != null && (
            <span className="text-foreground">
              <span className="font-display text-4xl tracking-wide">{Math.round(totalKm)}</span>
              <span className="text-[13px] text-muted-foreground ml-1">km</span>
            </span>
          )}
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <XAxis
              dataKey="day"
              tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: "hsl(var(--muted-foreground))" }}
              formatter={(value: number | undefined, name?: string) => {
                const label =
                  name === "easy"
                    ? "Easy"
                    : name === "tempo"
                      ? "Tempo"
                      : name === "long"
                        ? "Long"
                        : name ?? "";
                return [value != null ? `${value.toFixed(1)} km` : "", label];
              }}
              labelFormatter={(label) => label}
            />
            <Bar dataKey="easy" stackId="volume" fill={EASY_COLOR} radius={[0, 0, 0, 0]}>
              {data.map((_, i) => (
                <Cell key={`easy-${i}`} fill={EASY_COLOR} />
              ))}
            </Bar>
            <Bar dataKey="tempo" stackId="volume" fill={TEMPO_COLOR} radius={[0, 0, 0, 0]}>
              {data.map((_, i) => (
                <Cell key={`tempo-${i}`} fill={TEMPO_COLOR} />
              ))}
            </Bar>
            <Bar dataKey="long" stackId="volume" fill={LONG_COLOR} radius={[14, 14, 0, 0]}>
              {data.map((_, i) => (
                <Cell key={`long-${i}`} fill={LONG_COLOR} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex items-center justify-center gap-4 mt-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span
              className="size-2 rounded-full shrink-0"
              style={{ backgroundColor: EASY_COLOR }}
            />
            Easy
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="size-2 rounded-full shrink-0"
              style={{ backgroundColor: TEMPO_COLOR }}
            />
            Tempo
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="size-2 rounded-full shrink-0"
              style={{ backgroundColor: LONG_COLOR }}
            />
            Long
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
