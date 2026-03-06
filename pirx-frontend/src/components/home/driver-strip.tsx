"use client";

import { Card, CardContent } from "@/components/ui/card";
import Link from "next/link";
import { TrendingUp, Minus, TrendingDown } from "lucide-react";

interface Driver {
  name: string;
  displayName: string;
  contributionSeconds: number;
  trend: "improving" | "stable" | "declining";
  score: number;
}

const MOCK_DRIVERS: Driver[] = [
  { name: "aerobic_base", displayName: "Aerobic Base", contributionSeconds: 23.4, trend: "improving", score: 72 },
  { name: "threshold_density", displayName: "Threshold", contributionSeconds: 19.5, trend: "improving", score: 65 },
  { name: "speed_exposure", displayName: "Speed", contributionSeconds: 11.7, trend: "stable", score: 48 },
  { name: "running_economy", displayName: "Economy", contributionSeconds: 12.2, trend: "stable", score: 58 },
  { name: "load_consistency", displayName: "Consistency", contributionSeconds: 11.2, trend: "improving", score: 70 },
];

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
  const drivers = apiData ?? MOCK_DRIVERS;
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
