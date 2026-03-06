"use client";

import {
  LineChart,
  Line,
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

interface ProjectionHistoryChartProps {
  data: DataPoint[];
  baselineTime?: number;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export function ProjectionHistoryChart({
  data,
  baselineTime,
}: ProjectionHistoryChartProps) {
  if (data.length === 0) {
    return (
      <div className="h-[180px] flex items-center justify-center text-xs text-muted-foreground">
        No projection history yet
      </div>
    );
  }

  const minTime = Math.min(...data.map((d) => d.time)) - 10;
  const maxTime = Math.max(...data.map((d) => d.time)) + 10;

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
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
          formatter={(value: number | undefined) => [
            value != null ? formatTime(value) : "",
            "Projected",
          ]}
        />
        {baselineTime && (
          <ReferenceLine
            y={baselineTime}
            stroke="hsl(var(--destructive))"
            strokeDasharray="5 5"
            opacity={0.5}
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
      </LineChart>
    </ResponsiveContainer>
  );
}
