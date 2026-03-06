"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import Link from "next/link";
import {
  TrendingDown,
  TrendingUp,
  Minus,
  Timer,
  BarChart3,
  Target,
  Zap,
} from "lucide-react";

// Mock fitness snapshot data
const SNAPSHOT = [
  {
    event: "1500",
    name: "1500m",
    projected: "5:42",
    rangeLow: "5:35",
    rangeHigh: "5:48",
    baseline: "5:55",
    improvement: 13,
    change21d: 3,
    trend: "improving",
  },
  {
    event: "3000",
    name: "3K",
    projected: "12:18",
    rangeLow: "12:05",
    rangeHigh: "12:30",
    baseline: "12:50",
    improvement: 32,
    change21d: 8,
    trend: "improving",
  },
  {
    event: "5000",
    name: "5K",
    projected: "19:42",
    rangeLow: "19:15",
    rangeHigh: "20:08",
    baseline: "21:00",
    improvement: 78,
    change21d: 5,
    trend: "improving",
  },
  {
    event: "10000",
    name: "10K",
    projected: "43:15",
    rangeLow: "42:30",
    rangeHigh: "43:58",
    baseline: "45:00",
    improvement: 105,
    change21d: 12,
    trend: "improving",
  },
];

const trendConfig: Record<
  string,
  { icon: typeof TrendingUp; color: string; label: string }
> = {
  improving: { icon: TrendingDown, color: "text-green-500", label: "Improving" },
  stable: { icon: Minus, color: "text-muted-foreground", label: "Stable" },
  declining: { icon: TrendingUp, color: "text-red-500", label: "Declining" },
};

function FitnessSnapshotTable() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Timer className="h-4 w-4" />
          Fitness Snapshot
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">Event</TableHead>
              <TableHead className="text-xs text-right">Projected</TableHead>
              <TableHead className="text-xs text-right">Range</TableHead>
              <TableHead className="text-xs text-right">Change</TableHead>
              <TableHead className="text-xs text-center">Trend</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {SNAPSHOT.map((s) => {
              const { icon: TrendIcon, color } =
                trendConfig[s.trend] || trendConfig.stable;
              return (
                <TableRow
                  key={s.event}
                  className="cursor-pointer hover:bg-muted/50"
                >
                  <TableCell>
                    <Link
                      href={`/event/${s.event}`}
                      className="font-medium text-sm"
                    >
                      {s.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="font-bold tabular-nums text-sm">
                      {s.projected}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {s.rangeLow} – {s.rangeHigh}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <span
                      className={`text-sm font-medium tabular-nums ${color}`}
                    >
                      -{s.improvement}s
                    </span>
                  </TableCell>
                  <TableCell className="text-center">
                    <TrendIcon className={`h-4 w-4 mx-auto ${color}`} />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function PerformanceSummary() {
  return (
    <div className="grid grid-cols-3 gap-3">
      <Card>
        <CardContent className="p-3 text-center">
          <p className="text-[10px] text-muted-foreground">
            Total Improvement
          </p>
          <p className="text-lg font-bold tabular-nums text-green-500">-78s</p>
          <p className="text-[10px] text-muted-foreground">on 5K</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-3 text-center">
          <p className="text-[10px] text-muted-foreground">21-Day Change</p>
          <p className="text-lg font-bold tabular-nums text-green-500">-5s</p>
          <p className="text-[10px] text-muted-foreground">on 5K</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-3 text-center">
          <p className="text-[10px] text-muted-foreground">Readiness</p>
          <p className="text-lg font-bold tabular-nums">82</p>
          <p className="text-[10px] text-muted-foreground">/100</p>
        </CardContent>
      </Card>
    </div>
  );
}

export default function PerformancePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Performance</h1>

      <Tabs defaultValue="snapshot">
        <TabsList className="w-full">
          <TabsTrigger value="snapshot" className="flex-1">
            Snapshot
          </TabsTrigger>
          <TabsTrigger value="trends" className="flex-1">
            Trends
          </TabsTrigger>
          <TabsTrigger value="adjuncts" className="flex-1">
            Adjuncts
          </TabsTrigger>
        </TabsList>

        <TabsContent value="snapshot" className="space-y-6 mt-4">
          <PerformanceSummary />
          <FitnessSnapshotTable />

          {/* Baseline Info */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Baseline Race</p>
                    <p className="text-xs text-muted-foreground">
                      5K — 21:00 (Feb 15, 2026)
                    </p>
                  </div>
                </div>
                <Badge variant="secondary">Active</Badge>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="trends" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <BarChart3 className="h-4 w-4" /> Projection Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[200px] flex items-center justify-center rounded-lg bg-muted/30">
                <p className="text-xs text-muted-foreground">
                  Projection trend chart — coming with Recharts
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="adjuncts" className="space-y-4 mt-4">
          <Card>
            <CardContent className="p-6 text-center space-y-2">
              <Zap className="h-8 w-8 text-muted-foreground mx-auto" />
              <p className="text-sm text-muted-foreground">
                Adjunct Analysis will appear here once you have enough data.
              </p>
              <p className="text-xs text-muted-foreground">
                Patterns detected across pace, heart rate, and environmental
                data.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
