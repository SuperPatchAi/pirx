"use client";

import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface DataPoint {
  date: string;
  time: number;
}

interface RangePoint {
  date: string;
  low: number;
  high: number;
}

interface ProjectionHistoryChartProps {
  data: DataPoint[];
  baselineTime?: number;
  rangeData?: RangePoint[];
}

function formatTime(seconds: number): string {
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.round(seconds % 60);
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function ProjectionHistoryChart({
  data,
  baselineTime,
  rangeData,
}: ProjectionHistoryChartProps) {
  if (data.length === 0) {
    return (
      <div className="h-[280px] flex items-center justify-center text-sm text-muted-foreground">
        No projection history yet
      </div>
    );
  }

  const merged = data.map((d) => {
    const range = rangeData?.find((r) => r.date === d.date);
    return {
      ...d,
      range: range ? [range.low, range.high] : undefined,
    };
  });

  const allValues = [
    ...data.map((d) => d.time),
    ...(rangeData?.flatMap((r) => [r.low, r.high]) ?? []),
  ];
  const minTime = Math.min(...allValues) - 15;
  const maxTime = Math.max(...allValues) + 15;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart
        data={merged}
        margin={{ top: 10, right: 15, left: 5, bottom: 10 }}
      >
        <defs>
          <linearGradient id="rangeFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.25} />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.08} />
          </linearGradient>
          <linearGradient id="lineFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="hsl(var(--border))"
          opacity={0.5}
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={{ stroke: "hsl(var(--border))" }}
          tickFormatter={(d) => {
            const date = new Date(d);
            return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
          }}
          interval="preserveStartEnd"
          minTickGap={40}
        />
        <YAxis
          domain={[minTime, maxTime]}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={formatTime}
          reversed
          width={50}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px",
            fontSize: "13px",
            padding: "8px 12px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
          }}
          labelStyle={{ color: "hsl(var(--muted-foreground))", marginBottom: "4px" }}
          labelFormatter={(label) => {
            const date = new Date(label);
            return date.toLocaleDateString("en-US", { month: "long", day: "numeric" });
          }}
          formatter={(value: number | number[] | undefined, name: string | undefined) => {
            if (name === "range" && Array.isArray(value)) {
              return [
                `${formatTime(value[0])} – ${formatTime(value[1])}`,
                "Supported Range",
              ];
            }
            if (typeof value === "number") {
              return [formatTime(value), "Projected"];
            }
            return ["", ""];
          }}
        />
        {baselineTime && (
          <ReferenceLine
            y={baselineTime}
            stroke="hsl(var(--destructive))"
            strokeDasharray="6 4"
            opacity={0.7}
            label={{
              value: `Baseline ${formatTime(baselineTime)}`,
              position: "right",
              fill: "hsl(var(--destructive))",
              fontSize: 10,
            }}
          />
        )}
        {rangeData && rangeData.length > 0 && (
          <Area
            type="monotone"
            dataKey="range"
            fill="url(#rangeFill)"
            stroke="hsl(var(--primary))"
            strokeWidth={0}
            strokeOpacity={0}
            fillOpacity={1}
            activeDot={false}
            isAnimationActive={false}
          />
        )}
        <Area
          type="monotone"
          dataKey="time"
          fill="url(#lineFill)"
          stroke="none"
        />
        <Line
          type="monotone"
          dataKey="time"
          stroke="hsl(var(--primary))"
          strokeWidth={2.5}
          dot={false}
          activeDot={{ r: 5, fill: "hsl(var(--primary))", strokeWidth: 2, stroke: "hsl(var(--background))" }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
