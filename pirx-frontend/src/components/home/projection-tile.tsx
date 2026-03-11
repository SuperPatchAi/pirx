"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { motion } from "framer-motion";
import { TrendingDown, TrendingUp, ChevronDown, ChevronUp, Loader2 } from "lucide-react";

interface ProjectionTileProps {
  event: string;
  projectedTime: string;
  range: string;
  improvementSeconds: number;
  twentyOneDayChange: number | null;
  modelSource?: string | null;
  modelConfidence?: number | null;
  fallbackReason?: string | null;
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

function humanizeModelSource(source: string): string {
  const normalized = source.toLowerCase();
  if (normalized === "lstm") return "LSTM model";
  if (normalized === "deterministic") return "Deterministic model";
  if (normalized === "knn") return "KNN model";
  return `${source.toUpperCase()} model`;
}

function humanizeFallbackReason(reason: string): string {
  const map: Record<string, string> = {
    fallback_from_lstm_unavailable: "LSTM unavailable, using deterministic projection",
    fallback_from_lstm: "LSTM disabled for serving, using deterministic projection",
    fallback_from_knn: "KNN disabled for serving, using deterministic projection",
  };
  return map[reason] ?? reason.replaceAll("_", " ");
}

export function ProjectionTile({
  event,
  projectedTime,
  range,
  improvementSeconds,
  twentyOneDayChange,
  modelSource,
  modelConfidence,
  fallbackReason,
}: ProjectionTileProps) {
  const [showExplainer, setShowExplainer] = useState(false);
  const [explainerData, setExplainerData] = useState<ExplainerData | null>(null);
  const [explainerLoading, setExplainerLoading] = useState(false);

  const improving = improvementSeconds > 0;

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

  const has21DayDelta =
    typeof twentyOneDayChange === "number" && Number.isFinite(twentyOneDayChange);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="border-border/60 bg-card overflow-hidden relative glow-green-lg">
        <div className="absolute inset-0 bg-gradient-to-b from-green-500/6 to-transparent pointer-events-none" />
        <CardContent className="p-5 space-y-4 relative">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              {formatEventName(event)} Projection
            </span>
            {improving ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-green-500">
                <TrendingDown className="h-3.5 w-3.5" /> Improving
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-orange-400">
                <TrendingUp className="h-3.5 w-3.5" /> Trending Up
              </span>
            )}
          </div>

          {(modelSource || modelConfidence != null || fallbackReason) && (
            <div className="flex items-center gap-2">
              {modelSource && (
                <span className="inline-flex items-center rounded-full border border-border/60 px-2 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                  {humanizeModelSource(modelSource)}
                </span>
              )}
              {modelConfidence != null && (
                <span className="inline-flex items-center rounded-full border border-border/60 px-2 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                  {Math.round(modelConfidence * 100)}% confidence
                </span>
              )}
              {fallbackReason && (
                <span className="text-[10px] text-muted-foreground/80">{humanizeFallbackReason(fallbackReason)}</span>
              )}
            </div>
          )}

          <div>
            <p className="text-5xl font-extrabold tabular-nums tracking-tight text-green-500 leading-none">
              {projectedTime}
            </p>
          </div>

          <div className="flex items-center gap-6">
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">
                {improvementSeconds > 0 ? "-" : "+"}{Math.abs(improvementSeconds).toFixed(1)}s
              </p>
              <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wide">vs baseline</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">
                {has21DayDelta
                  ? `${twentyOneDayChange > 0 ? "-" : "+"}${Math.abs(twentyOneDayChange).toFixed(1)}s`
                  : "—"}
              </p>
              <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wide">21-day</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">{range}</p>
              <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wide">range</p>
            </div>
          </div>

          <button
            onClick={toggleExplainer}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors pt-1"
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
                    {explainerData.drivers.map((d) => {
                      const cs = Number(d.contribution_seconds) || 0;
                      return (
                        <div key={d.driver_name} className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">{d.display_name}</span>
                          <span className={`font-medium tabular-nums ${cs < 0 ? "text-green-500" : cs > 0 ? "text-red-400" : "text-muted-foreground"}`}>
                            {cs < 0 ? "" : "+"}{cs.toFixed(1)}s
                          </span>
                        </div>
                      );
                    })}
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
