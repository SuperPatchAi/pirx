"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { Timer, TrendingDown } from "lucide-react";

interface ProjectionTileProps {
  event: string;
  projectedTime: string;
  range: string;
  improvementSeconds: number;
  twentyOneDayChange: number;
}

function formatEventName(event: string): string {
  const names: Record<string, string> = {
    "1500": "1500m",
    "3000": "3K",
    "5000": "5K",
    "10000": "10K",
  };
  return names[event] || event;
}

export function ProjectionTile({
  event,
  projectedTime,
  range,
  improvementSeconds,
  twentyOneDayChange,
}: ProjectionTileProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
        <CardContent className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Timer className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium text-muted-foreground">
                Projected Time
              </span>
            </div>
            <Badge variant="secondary">{formatEventName(event)}</Badge>
          </div>

          <div className="space-y-1">
            <p className="text-4xl font-bold tabular-nums tracking-tight">
              {projectedTime}
            </p>
            <p className="text-sm text-muted-foreground">
              Supported Range: {range}
            </p>
          </div>

          <div className="flex items-center gap-4 pt-2">
            <div className="flex items-center gap-1">
              <TrendingDown className="h-3.5 w-3.5 text-green-500" />
              <span className="text-sm font-medium text-green-500">
                {improvementSeconds > 0 ? "-" : "+"}{Math.abs(improvementSeconds)}s
              </span>
              <span className="text-xs text-muted-foreground">total</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-sm font-medium text-green-500">
                {twentyOneDayChange > 0 ? "-" : "+"}{Math.abs(twentyOneDayChange)}s
              </span>
              <span className="text-xs text-muted-foreground">21-day</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
