"use client";

import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import Link from "next/link";
import { TrendingUp, Minus, TrendingDown, BarChart3 } from "lucide-react";

interface Driver {
  name: string;
  displayName: string;
  contributionSeconds: number;
  trend: "improving" | "stable" | "declining";
  score: number;
}

const trendConfig = {
  improving: { icon: TrendingUp, color: "text-green-500" },
  stable: { icon: Minus, color: "text-muted-foreground" },
  declining: { icon: TrendingDown, color: "text-red-500" },
};

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

export function DriverStrip({ apiData }: DriverStripProps) {
  const drivers = apiData ?? [];

  if (drivers.length === 0) {
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground">
          What&apos;s Driving Your Improvement
        </h3>
        <EmptyState
          icon={BarChart3}
          message="No driver data yet"
          submessage="Sync data to see what's driving your improvement"
        />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-muted-foreground">
        What&apos;s Driving Your Improvement
      </h3>
      <div className="grid grid-cols-5 gap-2">
        {drivers.map((d) => {
          const { icon: TrendIcon, color } = trendConfig[d.trend];
          return (
            <Link key={d.name} href={`/driver/${d.name}`}>
              <Card className="hover:border-primary/50 transition-colors">
                <CardContent className="p-2 text-center space-y-1">
                  <p className="text-[10px] text-muted-foreground truncate">
                    {d.displayName}
                  </p>
                  <p className="text-sm font-bold tabular-nums">
                    -{d.contributionSeconds}s
                  </p>
                  <TrendIcon className={`h-3 w-3 mx-auto ${color}`} />
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
