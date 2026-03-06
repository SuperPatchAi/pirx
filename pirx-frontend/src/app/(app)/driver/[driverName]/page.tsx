"use client";

import { useState, useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { motion } from "framer-motion";
import {
  ChevronLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  Lightbulb,
  BarChart3,
  Info,
  Loader2,
} from "lucide-react";
import { DriverScoreChart } from "@/components/charts/driver-score-chart";

const EMPTY_FACTORS: { feature: string; impact: string; direction: "positive" | "negative" }[] = [];

const trendConfig = {
  improving: {
    icon: TrendingUp,
    label: "Improving",
    color: "text-green-500",
    bgColor: "bg-green-500/10",
  },
  stable: {
    icon: Minus,
    label: "Stable",
    color: "text-muted-foreground",
    bgColor: "bg-muted",
  },
  declining: {
    icon: TrendingDown,
    label: "Declining",
    color: "text-red-500",
    bgColor: "bg-red-500/10",
  },
};

export default function DriverPage() {
  const router = useRouter();
  const params = useParams();
  const driverName = params.driverName as string;

  const [loading, setLoading] = useState(true);
  const [driverDetail, setDriverDetail] = useState<{
    displayName: string;
    description: string;
    score: number;
    trend: "improving" | "stable" | "declining";
    contribution: number;
  } | null>(null);
  const [scoreHistory, setScoreHistory] = useState<{ date: string; score: number }[] | null>(null);
  const [shapExplanation, setShapExplanation] = useState<{
    factors: { feature: string; impact: string; direction: "positive" | "negative" }[];
    insight: string;
  } | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const { apiFetch } = await import("@/lib/api");
        const [detail, explain] = await Promise.allSettled([
          apiFetch(`/drivers/${encodeURIComponent(driverName)}`),
          apiFetch(`/drivers/${encodeURIComponent(driverName)}/explain`),
        ]);

        if (detail.status === "fulfilled") {
          const d = detail.value as {
            name?: string;
            display_name?: string;
            description?: string;
            score?: number;
            trend?: string;
            contribution_seconds?: number;
            history?: Array<{ date: string; score: number }>;
          };
          setDriverDetail({
            displayName: d.display_name ?? driverName.replace(/_/g, " "),
            description: d.description ?? "",
            score: d.score ?? 0,
            trend: (d.trend as "improving" | "stable" | "declining") ?? "stable",
            contribution: d.contribution_seconds ?? 0,
          });
          if (d.history && d.history.length > 0) {
            setScoreHistory(d.history);
          }
        }

        if (explain.status === "fulfilled") {
          const e = explain.value as {
            top_factors?: Array<{ name: string; impact: number }>;
            narrative?: string;
          };
          if (e.top_factors || e.narrative) {
            setShapExplanation({
              factors: (e.top_factors ?? []).map((f) => ({
                feature: f.name,
                impact: `${f.impact > 0 ? "+" : ""}${f.impact.toFixed(1)}s`,
                direction: f.impact >= 0 ? "positive" : "negative",
              })),
              insight: e.narrative ?? "",
            });
          }
        }
      } catch {
        // Use mock on failure
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [driverName]);

  const data = {
    displayName: driverDetail?.displayName ?? driverName.replace(/_/g, " "),
    description: driverDetail?.description ?? "",
    score: driverDetail?.score ?? 0,
    trend: driverDetail?.trend ?? ("stable" as const),
    contribution: driverDetail?.contribution ?? 0,
    factors: shapExplanation?.factors ?? EMPTY_FACTORS,
    insight: shapExplanation?.insight ?? "",
  };
  const trend = trendConfig[data.trend];
  const TrendIcon = trend.icon;

  const chartData = useMemo(() => {
    if (scoreHistory && scoreHistory.length > 0) return scoreHistory;
    return Array.from({ length: 42 }, (_, i) => {
      const date = new Date(2026, 2, 5);
      date.setDate(date.getDate() - (41 - i));
      return {
        date: date.toISOString().split("T")[0],
        score: Math.min(
          100,
          45 + (i * (data.score - 45)) / 42 + (Math.random() - 0.5) * 5
        ),
      };
    });
  }, [scoreHistory, data.score]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" aria-label="Go back" onClick={() => router.back()}>
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {data.displayName}
          </h1>
          <p className="text-sm text-muted-foreground">Structural Driver</p>
        </div>
      </div>

      {/* Score Card */}
      <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Driver Score</p>
              <p className="text-5xl font-bold tabular-nums">{data.score}</p>
              <p className="text-xs text-muted-foreground">/100</p>
            </div>
            <div className="text-right space-y-2">
              <Badge className={`${trend.bgColor} ${trend.color} border-0`}>
                <TrendIcon className="mr-1 h-3 w-3" />
                {trend.label}
              </Badge>
              <p className="text-lg font-bold tabular-nums text-green-500">
                -{data.contribution}s
              </p>
              <p className="text-xs text-muted-foreground">contribution</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Description */}
      <Card>
        <CardContent className="p-4 flex gap-3">
          <Info className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
          <p className="text-sm text-muted-foreground">{data.description}</p>
        </CardContent>
      </Card>

      {/* Score History Chart Placeholder */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Score History (42 days)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DriverScoreChart data={chartData} />
        </CardContent>
      </Card>

      <Separator />

      {/* What's Contributing */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground">
          What&apos;s Contributing
        </h3>
        {data.factors.map((f, i) => (
          <Card key={i}>
            <CardContent className="flex items-center justify-between p-3">
              <span className="text-sm">{f.feature}</span>
              <span
                className={`text-sm font-bold tabular-nums ${
                  f.direction === "positive" ? "text-green-500" : "text-red-500"
                }`}
              >
                {f.impact}
              </span>
            </CardContent>
          </Card>
        ))}
      </div>

      <Separator />

      {/* AI Insight */}
      <Card className="bg-muted/30">
        <CardContent className="p-4 flex gap-3">
          <Lightbulb className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium mb-1">PIRX Insight</p>
            <p className="text-sm text-muted-foreground">{data.insight}</p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
