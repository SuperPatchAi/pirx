"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type SkeletonVariant = "projection" | "metric" | "chart" | "strip";

const STRIP_BAR_WIDTHS = ["45%", "62%", "55%", "78%", "48%"] as const;

export function SkeletonCard({ variant = "chart" }: { variant?: SkeletonVariant }) {
  switch (variant) {
    case "projection":
      return (
        <Card className="h-[220px]">
          <CardContent className="flex flex-col gap-4 pt-6">
            <Skeleton className="h-10 w-32" />
            <div className="flex gap-4">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-16" />
            </div>
          </CardContent>
        </Card>
      );
    case "metric":
      return (
        <Card className="h-[80px]">
          <CardContent className="flex flex-col items-center justify-center gap-2 pt-6">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-6 w-16" />
          </CardContent>
        </Card>
      );
    case "chart":
      return (
        <Card>
          <CardContent className="pt-6">
            <Skeleton className="h-[200px] w-full rounded-lg" />
          </CardContent>
        </Card>
      );
    case "strip":
      return (
        <Card>
          <CardContent className="flex flex-col gap-3 pt-6">
            {STRIP_BAR_WIDTHS.map((width, i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-3 w-12 shrink-0" />
                <div className="flex flex-1">
                  <Skeleton className="h-2" style={{ width }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      );
    default:
      return (
        <Card>
          <CardContent className="pt-6">
            <Skeleton className="h-[200px] w-full rounded-lg" />
          </CardContent>
        </Card>
      );
  }
}

export function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-10 w-full rounded-lg" />
      <SkeletonCard variant="projection" />
      <div className="flex gap-4 overflow-hidden">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="h-16 min-w-[120px] shrink-0">
            <CardContent className="flex items-center justify-center pt-4">
              <Skeleton className="h-4 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
      <SkeletonCard variant="strip" />
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <SkeletonCard key={i} variant="metric" />
        ))}
      </div>
    </div>
  );
}
