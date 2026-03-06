"use client";

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
} from "lucide-react";

// TODO: Replace with API data
const DRIVER_DATA: Record<
  string,
  {
    displayName: string;
    description: string;
    score: number;
    trend: "improving" | "stable" | "declining";
    contribution: number;
    factors: {
      feature: string;
      impact: string;
      direction: "positive" | "negative";
    }[];
    insight: string;
  }
> = {
  aerobic_base: {
    displayName: "Aerobic Base",
    description:
      "Volume and easy-effort training that builds your aerobic foundation. Driven by total distance, Zone 1-2 time, and long runs.",
    score: 72,
    trend: "improving",
    contribution: 23.4,
    factors: [
      {
        feature: "Weekly distance up 15%",
        impact: "+8.2s",
        direction: "positive",
      },
      {
        feature: "Z2 time increased",
        impact: "+5.1s",
        direction: "positive",
      },
      {
        feature: "Long run consistency",
        impact: "+3.4s",
        direction: "positive",
      },
    ],
    insight:
      "Your aerobic base has been your strongest driver over the past 3 weeks. Maintaining 40+ km/week with mostly easy runs is paying off.",
  },
  threshold_density: {
    displayName: "Threshold Density",
    description:
      "Time spent at threshold intensity (Zone 4) that raises your lactate ceiling and improves sustainable race pace.",
    score: 65,
    trend: "improving",
    contribution: 19.5,
    factors: [
      {
        feature: "Z4 time +12 min/week",
        impact: "+7.8s",
        direction: "positive",
      },
      {
        feature: "Matched HR band pace improving",
        impact: "+4.2s",
        direction: "positive",
      },
    ],
    insight:
      "You've added consistent threshold work. Consider maintaining current Z4 volume rather than increasing further.",
  },
  speed_exposure: {
    displayName: "Speed Exposure",
    description:
      "High-intensity work (Zone 5) that develops neuromuscular power and top-end speed.",
    score: 48,
    trend: "stable",
    contribution: 11.7,
    factors: [
      {
        feature: "Z5 time unchanged",
        impact: "0s",
        direction: "positive",
      },
    ],
    insight:
      "Speed work has been steady. Adding 1-2 short intervals per week could unlock further gains.",
  },
  running_economy: {
    displayName: "Running Economy",
    description:
      "How efficiently you convert energy to pace at a given heart rate. Improved through consistent strides and technique work.",
    score: 58,
    trend: "stable",
    contribution: 12.2,
    factors: [
      {
        feature: "HR drift improving",
        impact: "+3.1s",
        direction: "positive",
      },
      {
        feature: "Late session decay stable",
        impact: "+1.5s",
        direction: "positive",
      },
    ],
    insight:
      "Your economy is solid and holding. Strides after easy runs can further improve neuromuscular efficiency.",
  },
  load_consistency: {
    displayName: "Load Consistency",
    description:
      "Regularity of training load week-to-week. Consistent loading reduces injury risk and maximizes adaptation.",
    score: 70,
    trend: "improving",
    contribution: 11.2,
    factors: [
      {
        feature: "Weekly load variance decreased",
        impact: "+4.5s",
        direction: "positive",
      },
      {
        feature: "ACWR in safe zone (1.1)",
        impact: "+2.1s",
        direction: "positive",
      },
    ],
    insight:
      "Excellent consistency over the past month. Your ACWR is in the optimal training zone.",
  },
};

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
  const data = DRIVER_DATA[driverName] || DRIVER_DATA.aerobic_base;
  const trend = trendConfig[data.trend];
  const TrendIcon = trend.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
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
          <div className="h-[180px] flex items-center justify-center rounded-lg bg-muted/30">
            <p className="text-xs text-muted-foreground">
              Chart — coming with Recharts integration
            </p>
          </div>
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
