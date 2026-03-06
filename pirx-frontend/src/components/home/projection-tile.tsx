"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { Timer, TrendingDown, ChevronDown, ChevronUp, Loader2 } from "lucide-react";

interface ProjectionTileProps {
  event: string;
  projectedTime: string;
  range: string;
  improvementSeconds: number;
  twentyOneDayChange: number;
}

interface ExplainerData {
  event: string;
  narrative: string;
  drivers: Array<{
    driver_name: string;
    display_name: string;
    contribution_seconds: number;
    overall_direction: string;
    narrative: string;
    top_factors: Array<{ name: string; display_name: string; contribution: number; direction: string }>;
  }>;
  confidence: string;
}

function formatEventName(event: string): string {
  const names: Record<string, string> = {
    "1500": "1500m",
    "3000": "3K",
    "5000": "5K",
    "10000": "10K",
    "21097": "Half Marathon",
    "42195": "Marathon",
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
  const [showExplainer, setShowExplainer] = useState(false);
  const [explainerData, setExplainerData] = useState<ExplainerData | null>(null);
  const [explainerLoading, setExplainerLoading] = useState(false);

  async function toggleExplainer() {
    if (showExplainer) {
      setShowExplainer(false);
      return;
    }
    setShowExplainer(true);
    if (explainerData) return;

    setExplainerLoading(true);
    try {
      const { apiFetch } = await import("@/lib/api");
      const data = await apiFetch(`/projection/explain?event=${event}`);
      setExplainerData(data);
    } catch {
      setExplainerData(null);
    } finally {
      setExplainerLoading(false);
    }
  }

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

          <button
            onClick={toggleExplainer}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {showExplainer ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
            Why this number?
          </button>

          {showExplainer && (
            <div className="space-y-3 pt-1 border-t border-border/50">
              {explainerLoading ? (
                <div className="flex items-center gap-2 py-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">Analyzing projection...</span>
                </div>
              ) : explainerData ? (
                <>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {explainerData.narrative}
                  </p>
                  <div className="space-y-1.5">
                    {explainerData.drivers.map((d) => (
                      <div key={d.driver_name} className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">{d.display_name}</span>
                        <span className={`font-medium tabular-nums ${d.contribution_seconds < 0 ? "text-green-500" : d.contribution_seconds > 0 ? "text-red-500" : "text-muted-foreground"}`}>
                          {d.contribution_seconds < 0 ? "" : "+"}{d.contribution_seconds}s
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Unable to load explanation. Try again later.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
