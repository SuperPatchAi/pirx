"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import Link from "next/link";

interface AthleteCardProps {
  id: string;
  displayName: string;
  email: string;
  primaryEvent: string;
  projectedTime: string;
  readinessScore: number | null;
  twentyOneDayChange: number;
  status: string;
}

const EVENT_NAMES: Record<string, string> = {
  "1500": "1500m",
  "3000": "3K",
  "5000": "5K",
  "10000": "10K",
  "21097": "Half",
  "42195": "Marathon",
};

export function AthleteCard({
  id,
  displayName,
  email,
  primaryEvent,
  projectedTime,
  readinessScore,
  twentyOneDayChange,
  status,
}: AthleteCardProps) {
  if (status === "pending") {
    return (
      <Card className="opacity-60">
        <CardContent className="p-4">
          <p className="text-sm font-medium">{email}</p>
          <Badge variant="secondary" className="mt-1">
            Pending
          </Badge>
        </CardContent>
      </Card>
    );
  }

  const TrendIcon =
    twentyOneDayChange > 0
      ? TrendingDown
      : twentyOneDayChange < 0
        ? TrendingUp
        : Minus;
  const trendColor =
    twentyOneDayChange > 0
      ? "text-primary"
      : twentyOneDayChange < 0
        ? "text-red-500"
        : "text-muted-foreground";

  return (
    <Link href={`/coach/athlete/${id}`}>
      <Card className="hover:border-primary/50 transition-colors">
        <CardContent className="p-4 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">{displayName}</p>
            <Badge variant="secondary">
              {EVENT_NAMES[primaryEvent] || primaryEvent}
            </Badge>
          </div>
          <p className="text-2xl font-bold tabular-nums">{projectedTime}</p>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              <TrendIcon className={`h-3.5 w-3.5 ${trendColor}`} />
              <span className={`text-xs ${trendColor}`}>
                {twentyOneDayChange > 0 ? "-" : "+"}
                {Math.abs(twentyOneDayChange)}s 21d
              </span>
            </div>
            {readinessScore != null && (
              <span className="text-xs text-muted-foreground">
                Readiness: {readinessScore}/100
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
