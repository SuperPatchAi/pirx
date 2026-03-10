"use client";

import { AreaChart, Area, ResponsiveContainer } from "recharts";
import { Card, CardContent } from "@/components/ui/card";

const GREEN = "#22c55e";

export interface HrSparklineProps {
  data: { date: string; avg_hr: number }[] | null;
  avg: number | null;
  max: number | null;
}

export function HrSparkline({ data, avg, max }: HrSparklineProps) {
  const hasData = data && data.length > 0;

  return (
    <Card className="border-border/40">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] uppercase tracking-widest font-semibold text-muted-foreground">
            Heart Rate
          </span>
          {(avg != null || max != null) && (
            <span className="text-xs tabular-nums">
              {avg != null && (
                <span className="text-green-500 font-medium">{Math.round(avg)}</span>
              )}
              {avg != null && max != null && " avg  "}
              {max != null && (
                <span className="text-green-500 font-medium">{Math.round(max)}</span>
              )}
              {max != null && " max"}
            </span>
          )}
        </div>
        <div className="h-[50px] w-full">
          {hasData ? (
            <ResponsiveContainer width="100%" height={50}>
              <AreaChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
                <defs>
                  <linearGradient id="hrGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={GREEN} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={GREEN} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="avg_hr"
                  stroke={GREEN}
                  strokeWidth={1.5}
                  fill="url(#hrGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
              No data yet
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
