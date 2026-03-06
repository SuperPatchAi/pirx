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
      <div className="h-[180px] flex items-center justify-center text-xs text-muted-foreground">
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
  const minTime = Math.min(...allValues) - 10;
  const maxTime = Math.max(...allValues) + 10;

  return (
    <ResponsiveContainer width="100%" height={180}>
      <ComposedChart
        data={merged}
        margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
      >
        <defs>
          <linearGradient id="rangeFill" x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="0%"
              stopColor="hsl(var(--primary))"
              stopOpacity={0.15}
            />
            <stop
              offset="100%"
              stopColor="hsl(var(--primary))"
              stopOpacity={0.05}
            />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="hsl(var(--border))"
          opacity={0.3}
        />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(d) => {
            const date = new Date(d);
            return `${date.getMonth() + 1}/${date.getDate()}`;
          }}
        />
        <YAxis
          domain={[minTime, maxTime]}
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={formatTime}
          reversed
          width={45}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          labelStyle={{ color: "hsl(var(--muted-foreground))" }}
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
            strokeDasharray="5 5"
            opacity={0.5}
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
        <Line
          type="monotone"
          dataKey="time"
          stroke="hsl(var(--primary))"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: "hsl(var(--primary))" }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
