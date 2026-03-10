"use client";

import { useState, useEffect, useCallback } from "react";
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import Link from "next/link";
import {
  TrendingDown,
  TrendingUp,
  Minus,
  Timer,
  BarChart3,
  Target,
  Zap,
  Loader2,
  ChevronDown,
  Brain,
  Heart,
  Activity,
  BookOpen,
  Shield,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { ProjectionHistoryChart } from "@/components/charts/projection-history-chart";
import { apiFetch } from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from "recharts";

/* ────────────────────────────────────────────────────────────
   Helpers
   ──────────────────────────────────────────────────────────── */

function formatTime(seconds: number): string {
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.round(seconds % 60);
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatDelta(seconds: number): string {
  const sign = seconds >= 0 ? "+" : "";
  return `${sign}${Number(seconds).toFixed(1)}s`;
}

function roundNum(n: number, decimals = 1): string {
  return Number(n).toFixed(decimals);
}

function NoData({ message }: { message?: string }) {
  return (
    <Card>
      <CardContent className="p-6 text-center">
        <p className="text-sm text-muted-foreground">
          {message ?? "Data not yet available"}
        </p>
      </CardContent>
    </Card>
  );
}

function TabSpinner() {
  return (
    <div className="flex items-center justify-center h-40">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Mock snapshot data (fallback)
   ──────────────────────────────────────────────────────────── */

const SNAPSHOT = [
  { event: "1500", name: "1500m", projected: "—", rangeLow: "—", rangeHigh: "—", baseline: "—", improvement: 0, change21d: 0, trend: "stable" },
  { event: "3000", name: "3K", projected: "—", rangeLow: "—", rangeHigh: "—", baseline: "—", improvement: 0, change21d: 0, trend: "stable" },
  { event: "5000", name: "5K", projected: "—", rangeLow: "—", rangeHigh: "—", baseline: "—", improvement: 0, change21d: 0, trend: "stable" },
  { event: "10000", name: "10K", projected: "—", rangeLow: "—", rangeHigh: "—", baseline: "—", improvement: 0, change21d: 0, trend: "stable" },
];

const trendConfig: Record<string, { icon: typeof TrendingUp; color: string; label: string }> = {
  improving: { icon: TrendingDown, color: "text-green-500", label: "Improving" },
  stable: { icon: Minus, color: "text-muted-foreground", label: "Stable" },
  declining: { icon: TrendingUp, color: "text-red-500", label: "Declining" },
};

type SnapshotRow = {
  event: string;
  name: string;
  projected: string;
  rangeLow: string;
  rangeHigh: string;
  baseline: string;
  improvement: number;
  change21d: number;
  trend: string;
};

const EVENT_NAMES: Record<string, string> = {
  "1500": "1500m",
  "3000": "3K",
  "5000": "5K",
  "10000": "10K",
};

/* ────────────────────────────────────────────────────────────
   Snapshot sub-components
   ──────────────────────────────────────────────────────────── */

function FitnessSnapshotTable({ snapshot }: { snapshot: SnapshotRow[] }) {
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
            {snapshot.map((s) => {
              const { icon: TrendIcon, color } = trendConfig[s.trend] || trendConfig.stable;
              return (
                <TableRow key={s.event} className="cursor-pointer hover:bg-muted/50">
                  <TableCell>
                    <Link href={`/event/${s.event}`} className="font-medium text-sm">{s.name}</Link>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="font-bold tabular-nums text-sm">{s.projected}</span>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="text-xs text-muted-foreground tabular-nums">{s.rangeLow} – {s.rangeHigh}</span>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={`text-sm font-medium tabular-nums ${color}`}>
                      {s.improvement > 0 ? "-" : "+"}{roundNum(Math.abs(s.improvement))}s
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

function PerformanceSummary({ improvement, change21d, readiness }: { improvement: number; change21d: number; readiness: number }) {
  const impColor = improvement > 0 ? "text-green-500" : improvement < 0 ? "text-red-500" : "text-muted-foreground";
  const changeColor = change21d > 0 ? "text-green-500" : change21d < 0 ? "text-red-500" : "text-muted-foreground";
  return (
    <div className="grid grid-cols-3 gap-3">
      <Card>
        <CardContent className="p-3 text-center">
          <p className="text-[10px] text-muted-foreground">Total Improvement</p>
          <p className={`text-lg font-bold tabular-nums ${impColor}`}>
            {improvement > 0 ? "-" : "+"}{roundNum(Math.abs(improvement))}s
          </p>
          <p className="text-[10px] text-muted-foreground">on 5K</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-3 text-center">
          <p className="text-[10px] text-muted-foreground">21-Day Change</p>
          <p className={`text-lg font-bold tabular-nums ${changeColor}`}>
            {change21d > 0 ? "-" : "+"}{roundNum(Math.abs(change21d))}s
          </p>
          <p className="text-[10px] text-muted-foreground">on 5K</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-3 text-center">
          <p className="text-[10px] text-muted-foreground">Readiness</p>
          <p className="text-lg font-bold tabular-nums">{Math.round(readiness)}</p>
          <p className="text-[10px] text-muted-foreground">/100</p>
        </CardContent>
      </Card>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Drivers tab (5C)
   ──────────────────────────────────────────────────────────── */

const DRIVER_COLORS = ["#22c55e", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef4444"];

const DRIVER_DISPLAY: Record<string, string> = {
  aerobic_base: "Aerobic Base",
  threshold_density: "Threshold Density",
  speed_exposure: "Speed Exposure",
  running_economy: "Running Economy",
  load_consistency: "Load Consistency",
};

function driverLabel(name: string): string {
  return DRIVER_DISPLAY[name] ?? name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

interface Driver {
  name: string;
  display_name?: string;
  contribution_seconds: number;
  score: number;
}

interface DriverExplanation {
  top_factors: { name: string; impact: number }[];
  narrative: string;
}

function DriversTab({
  drivers,
  loading,
}: {
  drivers: Driver[] | null;
  loading: boolean;
}) {
  const [expandedDriver, setExpandedDriver] = useState<string | null>(null);
  const [explanations, setExplanations] = useState<Record<string, DriverExplanation>>({});
  const [explainLoading, setExplainLoading] = useState<string | null>(null);

  const fetchExplanation = useCallback(async (driverName: string) => {
    if (explanations[driverName]) return;
    setExplainLoading(driverName);
    try {
      const data = await apiFetch(`/drivers/${encodeURIComponent(driverName)}/explain`);
      setExplanations((prev) => ({ ...prev, [driverName]: data }));
    } catch {
      setExplanations((prev) => ({
        ...prev,
        [driverName]: { top_factors: [], narrative: "Unable to load explanation." },
      }));
    } finally {
      setExplainLoading(null);
    }
  }, [explanations]);

  if (loading) return <TabSpinner />;
  if (!drivers || drivers.length === 0) return <NoData message="Driver data not yet available" />;

  const chartData = drivers.map((d, i) => ({
    name: d.display_name ?? driverLabel(d.name),
    value: Math.abs(Number(d.contribution_seconds) || 0),
    fill: DRIVER_COLORS[i % DRIVER_COLORS.length],
    score: d.score,
    raw: d.contribution_seconds,
    key: d.name,
  }));

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="h-4 w-4" /> Driver Contributions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={drivers.length * 52 + 24}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 40, left: 10, bottom: 0 }}>
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickFormatter={(v: number) => `${v.toFixed(1)}s`}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 12, fill: "hsl(var(--foreground))", fontWeight: 500 }}
                width={130}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "13px",
                  padding: "8px 12px",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                }}
                formatter={(value: number | undefined, _name: string | undefined, props: { payload?: { key?: string; score?: number } }) => {
                  const score = props?.payload?.score ?? 0;
                  return [value != null ? `${value.toFixed(1)}s (score: ${score})` : "", "Contribution"];
                }}
                labelFormatter={(label) => String(label)}
              />
              <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={28}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {drivers.map((driver, i) => (
        <Collapsible
          key={driver.name}
          open={expandedDriver === driver.name}
          onOpenChange={(open) => {
            setExpandedDriver(open ? driver.name : null);
            if (open) fetchExplanation(driver.name);
          }}
        >
          <Card>
            <CollapsibleTrigger className="w-full text-left">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: DRIVER_COLORS[i % DRIVER_COLORS.length] }} />
                  <div>
                    <p className="text-sm font-medium">{driver.display_name ?? driverLabel(driver.name)}</p>
                    <p className="text-xs text-muted-foreground">Score: {Math.round(driver.score)} | {formatDelta(driver.contribution_seconds)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-xs">Why?</Badge>
                  <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform data-[state=open]:rotate-180" />
                </div>
              </CardContent>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="px-4 pb-4 pt-0 border-t">
                {explainLoading === driver.name ? (
                  <div className="flex items-center gap-2 py-3">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span className="text-xs text-muted-foreground">Loading explanation...</span>
                  </div>
                ) : explanations[driver.name] ? (
                  <div className="space-y-2 pt-3">
                    <p className="text-sm text-muted-foreground">{explanations[driver.name].narrative}</p>
                    {explanations[driver.name].top_factors.length > 0 && (
                      <div className="space-y-1">
                        <p className="text-xs font-medium">Top Factors</p>
                        {explanations[driver.name].top_factors.map((f) => (
                          <div key={f.name} className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground">{f.name}</span>
                            <span className="tabular-nums font-medium">{formatDelta(f.impact)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      ))}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Zones tab (5E)
   ──────────────────────────────────────────────────────────── */

const ZONE_COLORS = ["#94a3b8", "#22c55e", "#3b82f6", "#f59e0b", "#ef4444"];

interface ZonesData {
  zones: { name: string; hr_range: string; pace_range: string; time_pct: number }[];
  distribution: { zone: string; pct: number }[];
  methodology: string;
  z2_efficiency_gain: number;
}

function ZonesTab({ data, loading }: { data: ZonesData | null; loading: boolean }) {
  if (loading) return <TabSpinner />;
  if (!data) return <NoData message="No HR zone data yet. Sync activities with heart rate data to see your zone distribution." />;

  const pieData = (data.distribution ?? []).map((d, i) => ({
    name: d.zone,
    value: d.pct,
    fill: ZONE_COLORS[i % ZONE_COLORS.length],
  }));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-xs">{data.methodology}</Badge>
        <Badge variant="secondary" className="text-xs">
          Z2 Efficiency: {data.z2_efficiency_gain > 0 ? "+" : ""}{data.z2_efficiency_gain}%
        </Badge>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Training Zones</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Zone</TableHead>
                <TableHead className="text-xs">HR Range</TableHead>
                <TableHead className="text-xs">Pace Range</TableHead>
                <TableHead className="text-xs text-right">Time %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data.zones ?? []).map((z, i) => (
                <TableRow key={z.name}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: ZONE_COLORS[i % ZONE_COLORS.length] }} />
                      <span className="text-sm font-medium">{z.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs tabular-nums">{z.hr_range}</TableCell>
                  <TableCell className="text-xs tabular-nums">{z.pace_range}</TableCell>
                  <TableCell className="text-xs text-right tabular-nums font-medium">{z.time_pct}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {pieData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">21-Day Zone Distribution</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  innerRadius={40}
                  paddingAngle={2}
                  label={({ name, value }) => `${name}: ${value}%`}
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number | undefined) => [value != null ? `${value}%` : "", "Time"]} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Economy tab (5F)
   ──────────────────────────────────────────────────────────── */

interface EconomyData {
  matched_hr_band: { hr_range: string; baseline_pace: string; current_pace: string; efficiency_gain: number };
  hr_cost_change: number;
  intensity_levels: { level: string; baseline: string; current: string; delta: number }[];
}

function EconomyTab({ data, loading }: { data: EconomyData | null; loading: boolean }) {
  if (loading) return <TabSpinner />;
  if (!data) return <NoData message="Not enough matched-HR activities to compute running economy. Need at least 3 runs in the 145–155 bpm range." />;

  const band = data.matched_hr_band;

  return (
    <div className="space-y-4">
      {band && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Heart className="h-4 w-4" /> Matched HR Band
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] text-muted-foreground">HR Range</p>
                <p className="text-sm font-medium tabular-nums">{band.hr_range}</p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">Efficiency Gain</p>
                <p className="text-sm font-medium tabular-nums text-green-500">
                  {band.efficiency_gain > 0 ? "+" : ""}{band.efficiency_gain}%
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">Baseline Pace</p>
                <p className="text-sm tabular-nums">{band.baseline_pace}</p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">Current Pace</p>
                <p className="text-sm tabular-nums font-medium">{band.current_pace}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-4 text-center">
          <p className="text-[10px] text-muted-foreground">HR Cost Change</p>
          <p className={`text-2xl font-bold tabular-nums ${data.hr_cost_change <= 0 ? "text-green-500" : "text-red-500"}`}>
            {data.hr_cost_change > 0 ? "+" : ""}{data.hr_cost_change}%
          </p>
        </CardContent>
      </Card>

      {data.intensity_levels && data.intensity_levels.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Intensity Levels</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Level</TableHead>
                  <TableHead className="text-xs text-right">Baseline</TableHead>
                  <TableHead className="text-xs text-right">Current</TableHead>
                  <TableHead className="text-xs text-right">Delta</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.intensity_levels.map((lvl) => (
                  <TableRow key={lvl.level}>
                    <TableCell className="text-sm font-medium">{lvl.level}</TableCell>
                    <TableCell className="text-xs text-right tabular-nums">{lvl.baseline}</TableCell>
                    <TableCell className="text-xs text-right tabular-nums font-medium">{lvl.current}</TableCell>
                    <TableCell className={`text-xs text-right tabular-nums ${lvl.delta <= 0 ? "text-green-500" : "text-red-500"}`}>
                      {formatDelta(lvl.delta)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Readiness tab (5G)
   ──────────────────────────────────────────────────────────── */

interface ReadinessData {
  score: number;
  label: string;
  components?: { name: string; value: number }[];
}

function getReadinessColor(score: number): string {
  if (score >= 95) return "bg-green-500 text-white";
  if (score >= 88) return "bg-blue-500 text-white";
  if (score >= 75) return "bg-amber-500 text-white";
  if (score >= 60) return "bg-gray-400 text-white";
  return "bg-red-500 text-white";
}

function getReadinessRingColor(score: number): string {
  if (score >= 95) return "text-green-500";
  if (score >= 88) return "text-blue-500";
  if (score >= 75) return "text-amber-500";
  if (score >= 60) return "text-gray-400";
  return "text-red-500";
}

function ReadinessTab({ data, loading }: { data: ReadinessData | null; loading: boolean }) {
  if (loading) return <TabSpinner />;
  if (!data) return <NoData message="Sync a wearable to see your event readiness score." />;

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-6 flex flex-col items-center gap-3">
          <div className={`text-5xl font-bold tabular-nums ${getReadinessRingColor(data.score)}`}>
            {data.score}
          </div>
          <Badge className={getReadinessColor(data.score)}>{data.label}</Badge>
          <p className="text-xs text-muted-foreground">Event Readiness Score</p>
        </CardContent>
      </Card>

      {data.components && data.components.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Component Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.components.map((c) => (
              <div key={c.name} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">{c.name}</span>
                  <span className="font-medium tabular-nums">{c.value}</span>
                </div>
                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${Math.min(c.value, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Learning tab (5H)
   ──────────────────────────────────────────────────────────── */

interface LearningData {
  structural_identity: string | null;
  insights: { title: string; body: string; status: string; confidence: number }[];
  summary?: string;
}

const INSIGHT_STATUS_COLORS: Record<string, string> = {
  observational: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  emerging: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
  supported: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
};

function LearningTab({ data, loading }: { data: LearningData | null; loading: boolean }) {
  if (loading) return <TabSpinner />;
  if (!data) return <NoData message="Not enough training history to detect patterns yet. Keep syncing activities." />;

  return (
    <div className="space-y-4">
      {data.structural_identity && (
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <Brain className="h-5 w-5 text-primary" />
            <div>
              <p className="text-[10px] text-muted-foreground">Structural Identity</p>
              <p className="text-sm font-medium">{data.structural_identity}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {data.summary && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">{data.summary}</p>
          </CardContent>
        </Card>
      )}

      {(data.insights ?? []).map((insight, i) => {
        const statusLower = insight.status.toLowerCase();
        return (
          <Card key={i}>
            <CardContent className="p-4 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium">{insight.title}</p>
                <Badge className={`text-[10px] shrink-0 ${INSIGHT_STATUS_COLORS[statusLower] ?? ""}`}>
                  {insight.status}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">{insight.body}</p>
              <div className="flex items-center gap-2">
                <div className="h-1 flex-1 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${Math.min(insight.confidence * 100, 100)}%` }}
                  />
                </div>
                <span className="text-[10px] text-muted-foreground tabular-nums">
                  {Math.round(insight.confidence * 100)}%
                </span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Adjuncts tab (5I)
   ──────────────────────────────────────────────────────────── */

interface AdjunctItem {
  name: string;
  sessions_analyzed: number;
  median_projection_delta: number;
  hr_drift_change: number;
  volatility_change: number;
  status: string;
  confidence: number;
}

function AdjunctsTab({ data, loading }: { data: AdjunctItem[] | null; loading: boolean }) {
  if (loading) return <TabSpinner />;
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center space-y-2">
          <Zap className="h-8 w-8 text-muted-foreground mx-auto" />
          <p className="text-sm text-muted-foreground">
            Adjunct Analysis will appear here once you have enough data.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {data.map((adj) => {
        const statusLower = adj.status.toLowerCase();
        return (
          <Card key={adj.name}>
            <CardContent className="p-4 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium">{adj.name}</p>
                <Badge className={`text-[10px] shrink-0 ${INSIGHT_STATUS_COLORS[statusLower] ?? ""}`}>
                  {adj.status}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <p className="text-muted-foreground">Sessions</p>
                  <p className="font-medium tabular-nums">{adj.sessions_analyzed}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Projection Delta</p>
                  <p className={`font-medium tabular-nums ${adj.median_projection_delta <= 0 ? "text-green-500" : "text-red-500"}`}>
                    {formatDelta(adj.median_projection_delta)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">HR Drift</p>
                  <p className="font-medium tabular-nums">{formatDelta(adj.hr_drift_change)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Volatility</p>
                  <p className="font-medium tabular-nums">{formatDelta(adj.volatility_change)}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="h-1.5 flex-1 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${Math.min(adj.confidence * 100, 100)}%` }}
                  />
                </div>
                <span className="text-[10px] text-muted-foreground tabular-nums">
                  {Math.round(adj.confidence * 100)}%
                </span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Honest State tab (5J)
   ──────────────────────────────────────────────────────────── */

interface HonestStateSection {
  title: string;
  body: string;
}

interface HonestStateData {
  what_today_supports: HonestStateSection[];
  what_is_defensible: HonestStateSection[];
  what_needs_development: HonestStateSection[];
}

const SECTION_CONFIG = [
  {
    key: "what_today_supports" as const,
    label: "What Today Supports",
    icon: Shield,
    bg: "bg-green-50 dark:bg-green-950/30",
    border: "border-green-200 dark:border-green-900",
    iconColor: "text-green-600 dark:text-green-400",
  },
  {
    key: "what_is_defensible" as const,
    label: "What Is Defensible",
    icon: Activity,
    bg: "bg-blue-50 dark:bg-blue-950/30",
    border: "border-blue-200 dark:border-blue-900",
    iconColor: "text-blue-600 dark:text-blue-400",
  },
  {
    key: "what_needs_development" as const,
    label: "What Needs Development",
    icon: BookOpen,
    bg: "bg-amber-50 dark:bg-amber-950/30",
    border: "border-amber-200 dark:border-amber-900",
    iconColor: "text-amber-600 dark:text-amber-400",
  },
];

function HonestStateTab({ data, loading }: { data: HonestStateData | null; loading: boolean }) {
  if (loading) return <TabSpinner />;
  if (!data) return <NoData message="Honest State data not yet available" />;

  const hasAny = SECTION_CONFIG.some(({ key }) => (data[key]?.length ?? 0) > 0);
  if (!hasAny) return <NoData message="Not enough training data to determine your honest state yet. Sync a wearable to get started." />;

  return (
    <div className="space-y-4">
      {SECTION_CONFIG.map(({ key, label, icon: Icon, bg, border, iconColor }) => {
        const items = data[key];
        if (!items || items.length === 0) return null;
        return (
          <div key={key} className="space-y-2">
            <div className="flex items-center gap-2">
              <Icon className={`h-4 w-4 ${iconColor}`} />
              <h3 className="text-sm font-medium">{label}</h3>
            </div>
            {items.map((item, i) => (
              <Card key={i} className={`${bg} border ${border}`}>
                <CardContent className="p-4 space-y-1">
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{item.body}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        );
      })}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Accuracy tab (5K)
   ──────────────────────────────────────────────────────────── */

const EVENT_LABELS: Record<string, string> = {
  "1500": "1500m",
  "3000": "3K",
  "5000": "5K",
  "10000": "10K",
  "21097": "Half Marathon",
  "42195": "Marathon",
};

interface GlobalAccuracy {
  mae_seconds: number | null;
  bias_seconds: number | null;
  bland_altman_lower: number | null;
  bland_altman_upper: number | null;
  sample_size: number;
  meets_benchmark: boolean;
  benchmark_target: number;
  metric_date?: string;
}

interface RaceComparison {
  race_date: string;
  event: string;
  actual_seconds: number;
  projected_seconds: number;
  error_seconds: number;
}

interface UserAccuracy {
  races: RaceComparison[];
  mae_seconds: number | null;
  sample_size: number;
  meets_benchmark?: boolean;
}

function AccuracyTab({
  globalData,
  userData,
  loading,
}: {
  globalData: GlobalAccuracy | null;
  userData: UserAccuracy | null;
  loading: boolean;
}) {
  if (loading) return <TabSpinner />;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Target className="h-4 w-4" /> Global Model Accuracy
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {globalData && globalData.mae_seconds != null ? (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold tabular-nums">
                    {globalData.mae_seconds.toFixed(1)}s
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Mean Absolute Error
                  </p>
                </div>
                <Badge
                  variant={globalData.meets_benchmark ? "default" : "secondary"}
                  className="flex items-center gap-1"
                >
                  {globalData.meets_benchmark ? (
                    <CheckCircle className="h-3 w-3" />
                  ) : (
                    <XCircle className="h-3 w-3" />
                  )}
                  {globalData.meets_benchmark ? "Meets" : "Below"} {globalData.benchmark_target}s benchmark
                </Badge>
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div>
                  <p className="text-muted-foreground">Bias</p>
                  <p className="font-medium tabular-nums">
                    {globalData.bias_seconds != null ? `${globalData.bias_seconds > 0 ? "+" : ""}${globalData.bias_seconds.toFixed(1)}s` : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">95% Limits</p>
                  <p className="font-medium tabular-nums">
                    {globalData.bland_altman_lower != null && globalData.bland_altman_upper != null
                      ? `${globalData.bland_altman_lower.toFixed(0)}s to ${globalData.bland_altman_upper.toFixed(0)}s`
                      : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Sample Size</p>
                  <p className="font-medium tabular-nums">{globalData.sample_size}</p>
                </div>
              </div>
              {globalData.metric_date && (
                <p className="text-[10px] text-muted-foreground">
                  Last computed: {new Date(globalData.metric_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              No global accuracy data yet. Metrics are computed weekly.
            </p>
          )}
        </CardContent>
      </Card>

      {userData && userData.races.length > 0 && (
        <>
          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-lg font-bold tabular-nums">
                  {userData.mae_seconds != null ? `${userData.mae_seconds.toFixed(1)}s` : "—"}
                </p>
                <p className="text-xs text-muted-foreground">Your MAE ({userData.sample_size} races)</p>
              </div>
              {userData.meets_benchmark != null && (
                <Badge variant={userData.meets_benchmark ? "default" : "secondary"}>
                  {userData.meets_benchmark ? "Within target" : "Improving"}
                </Badge>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Race Comparisons</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Date</TableHead>
                    <TableHead className="text-xs">Event</TableHead>
                    <TableHead className="text-xs text-right">Actual</TableHead>
                    <TableHead className="text-xs text-right">Projected</TableHead>
                    <TableHead className="text-xs text-right">Error</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {userData.races.map((r, i) => (
                    <TableRow key={i}>
                      <TableCell className="text-xs tabular-nums">{r.race_date}</TableCell>
                      <TableCell className="text-xs font-medium">
                        {EVENT_LABELS[r.event] ?? r.event}
                      </TableCell>
                      <TableCell className="text-xs text-right tabular-nums">
                        {formatTime(r.actual_seconds)}
                      </TableCell>
                      <TableCell className="text-xs text-right tabular-nums">
                        {formatTime(r.projected_seconds)}
                      </TableCell>
                      <TableCell
                        className={`text-xs text-right tabular-nums font-medium ${
                          Math.abs(r.error_seconds) <= 7 ? "text-green-500" : "text-amber-500"
                        }`}
                      >
                        {formatDelta(r.error_seconds)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {userData && userData.races.length === 0 && (
        <NoData message="No race results to compare yet. Complete a race to see accuracy data." />
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Main Performance Page
   ──────────────────────────────────────────────────────────── */

export default function PerformancePage() {
  const [loading, setLoading] = useState(true);
  const [snapshot, setSnapshot] = useState<SnapshotRow[]>(SNAPSHOT);
  const [summary, setSummary] = useState({ improvement: 0, change21d: 0, readiness: 0 });
  const [trendsData, setTrendsData] = useState<{ date: string; time: number }[] | null>(null);
  const [trendsRangeData, setTrendsRangeData] = useState<{ date: string; low: number; high: number }[] | null>(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [fetchedTabs, setFetchedTabs] = useState<Set<string>>(new Set());
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [baseline, setBaseline] = useState<{ event: string; time_seconds: number; race_date: string | null } | null>(null);

  // Lazy-loaded tab state
  const [driversData, setDriversData] = useState<Driver[] | null>(null);
  const [driversLoading, setDriversLoading] = useState(false);
  const [zonesData, setZonesData] = useState<ZonesData | null>(null);
  const [zonesLoading, setZonesLoading] = useState(false);
  const [economyData, setEconomyData] = useState<EconomyData | null>(null);
  const [economyLoading, setEconomyLoading] = useState(false);
  const [readinessData, setReadinessData] = useState<ReadinessData | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [learningData, setLearningData] = useState<LearningData | null>(null);
  const [learningLoading, setLearningLoading] = useState(false);
  const [adjunctsData, setAdjunctsData] = useState<AdjunctItem[] | null>(null);
  const [adjunctsLoading, setAdjunctsLoading] = useState(false);
  const [honestStateData, setHonestStateData] = useState<HonestStateData | null>(null);
  const [honestStateLoading, setHonestStateLoading] = useState(false);
  const [accuracyGlobal, setAccuracyGlobal] = useState<GlobalAccuracy | null>(null);
  const [accuracyUser, setAccuracyUser] = useState<UserAccuracy | null>(null);
  const [accuracyLoading, setAccuracyLoading] = useState(false);

  const markFetched = useCallback((tab: string) => {
    setFetchedTabs((prev) => new Set(prev).add(tab));
  }, []);

  // Initial snapshot/trends load
  useEffect(() => {
    async function load() {
      try {
        const events = ["1500", "3000", "5000", "10000"];
        const projCalls = events.map((e) => apiFetch(`/projection?event=${e}`));
        const [p1500, p3000, p5000, p10000, history] = await Promise.allSettled([
          ...projCalls,
          apiFetch("/projection/history?event=5000&days=90"),
        ]);

        const results = [p1500, p3000, p5000, p10000];
        const rows: SnapshotRow[] = events.map((eventId, i) => {
          const res = results[i];
          if (res.status === "fulfilled") {
            const p = res.value as {
              projected_time?: string;
              projected_time_seconds?: number;
              supported_range_low?: number;
              supported_range_high?: number;
              total_improvement_seconds?: number;
              twenty_one_day_change?: number;
            };
            const projSeconds = p.projected_time_seconds ?? 0;
            const improvement = p.total_improvement_seconds ?? 0;
            const baselineSeconds = projSeconds + improvement;
            return {
              event: eventId,
              name: EVENT_NAMES[eventId] ?? eventId,
              projected: p.projected_time ?? formatTime(projSeconds),
              rangeLow: p.supported_range_low != null ? formatTime(p.supported_range_low) : "",
              rangeHigh: p.supported_range_high != null ? formatTime(p.supported_range_high) : "",
              baseline: formatTime(baselineSeconds),
              improvement,
              change21d: p.twenty_one_day_change ?? 0,
              trend: "improving",
            };
          }
          return SNAPSHOT[i];
        });
        setSnapshot(rows);

        const p5k = results[2];
        let readinessScore = 0;
        try {
          const readinessRes = await apiFetch("/readiness");
          if (readinessRes && typeof readinessRes.score === "number") {
            readinessScore = readinessRes.score;
          }
        } catch {
          // fallback to default
        }

        try {
          const bl = await apiFetch("/account/baseline");
          if (bl && bl.event) {
            setBaseline({ event: bl.event, time_seconds: bl.time_seconds ?? 0, race_date: bl.race_date ?? null });
          }
        } catch {
          // baseline not available
        }

        if (p5k.status === "fulfilled") {
          const p = p5k.value as { total_improvement_seconds?: number; twenty_one_day_change?: number };
          setSummary({
            improvement: p.total_improvement_seconds ?? 0,
            change21d: p.twenty_one_day_change ?? 0,
            readiness: readinessScore,
          });
        } else {
          setSummary((prev) => ({ ...prev, readiness: readinessScore }));
        }

        if (history.status === "fulfilled") {
          const h = history.value as {
            history?: Array<{ date: string; projected_time_seconds?: number; range_low?: number; range_high?: number }>;
            points?: Array<{ date: string; projected_time_seconds?: number; range_low?: number; range_high?: number }>;
          };
          const points = h.history ?? h.points ?? [];
          setTrendsData(points.map((pt) => ({ date: pt.date, time: pt.projected_time_seconds ?? 0 })));
          const ranges = points
            .filter((pt) => pt.range_low != null && pt.range_high != null)
            .map((pt) => ({ date: pt.date, low: pt.range_low!, high: pt.range_high! }));
          if (ranges.length > 0) setTrendsRangeData(ranges);
        }
      } catch {
        // keep empty defaults on failure
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const lazyFetch = useCallback(
    (key: string, fetcher: () => void) => {
      if (!fetchedTabs.has(key)) {
        markFetched(key);
        fetcher();
      }
    },
    [fetchedTabs, markFetched]
  );

  const handleSectionToggle = useCallback(
    (section: string, open: boolean) => {
      setExpandedSection(open ? section : null);
      if (!open) return;

      const loaders: Record<string, () => void> = {
        drivers: () => {
          setDriversLoading(true);
          apiFetch("/drivers")
            .then((d) => {
              const raw = Array.isArray(d) ? d : d.drivers ?? [];
              const mapped: Driver[] = raw.map((item: Record<string, unknown>) => ({
                name: (item.driver_name ?? item.name ?? "") as string,
                display_name: (item.display_name ?? "") as string,
                contribution_seconds: Number(item.contribution_seconds ?? 0),
                score: Number(item.score ?? 0),
              }));
              setDriversData(mapped);
            })
            .catch(() => {})
            .finally(() => setDriversLoading(false));
        },
        zones: () => {
          setZonesLoading(true);
          apiFetch("/features/zones")
            .then(setZonesData)
            .catch(() => {})
            .finally(() => setZonesLoading(false));
        },
        economy: () => {
          setEconomyLoading(true);
          apiFetch("/features/economy")
            .then(setEconomyData)
            .catch(() => {})
            .finally(() => setEconomyLoading(false));
        },
        readiness: () => {
          setReadinessLoading(true);
          apiFetch("/readiness")
            .then((d) => {
              let components: { name: string; value: number }[] = [];
              if (d.components) {
                if (Array.isArray(d.components)) {
                  components = d.components;
                } else {
                  components = Object.entries(d.components).map(([k, v]) => ({
                    name: k.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
                    value: Number(v) || 0,
                  }));
                }
              }
              setReadinessData({ score: d.score ?? 0, label: d.label ?? "Unknown", components });
            })
            .catch(() => {})
            .finally(() => setReadinessLoading(false));
        },
        learning: () => {
          setLearningLoading(true);
          apiFetch("/features/learning")
            .then(setLearningData)
            .catch(() => {})
            .finally(() => setLearningLoading(false));
        },
        adjuncts: () => {
          setAdjunctsLoading(true);
          apiFetch("/features/adjuncts")
            .then((d) => setAdjunctsData(Array.isArray(d) ? d : d.adjuncts ?? []))
            .catch(() => {})
            .finally(() => setAdjunctsLoading(false));
        },
        "honest-state": () => {
          setHonestStateLoading(true);
          apiFetch("/features/honest-state")
            .then(setHonestStateData)
            .catch(() => {})
            .finally(() => setHonestStateLoading(false));
        },
        accuracy: () => {
          setAccuracyLoading(true);
          Promise.allSettled([apiFetch("/accuracy"), apiFetch("/accuracy/user")])
            .then(([globalRes, userRes]) => {
              if (globalRes.status === "fulfilled") setAccuracyGlobal(globalRes.value);
              if (userRes.status === "fulfilled") setAccuracyUser(userRes.value);
            })
            .finally(() => setAccuracyLoading(false));
        },
      };

      if (loaders[section]) lazyFetch(section, loaders[section]);
    },
    [lazyFetch]
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const ANALYSIS_SECTIONS = [
    { key: "drivers", label: "Structural Drivers", icon: BarChart3 },
    { key: "zones", label: "Zone Distribution", icon: Activity },
    { key: "economy", label: "Running Economy", icon: Heart },
    { key: "readiness", label: "Event Readiness", icon: Shield },
    { key: "learning", label: "What We're Learning", icon: Brain },
    { key: "adjuncts", label: "Adjunct Analysis", icon: Zap },
    { key: "honest-state", label: "Current Honest State", icon: BookOpen },
    { key: "accuracy", label: "Model Accuracy", icon: Target },
  ] as const;

  const renderAnalysisContent = (key: string) => {
    switch (key) {
      case "drivers":
        return <DriversTab drivers={driversData} loading={driversLoading} />;
      case "zones":
        return <ZonesTab data={zonesData} loading={zonesLoading} />;
      case "economy":
        return <EconomyTab data={economyData} loading={economyLoading} />;
      case "readiness":
        return <ReadinessTab data={readinessData} loading={readinessLoading} />;
      case "learning":
        return <LearningTab data={learningData} loading={learningLoading} />;
      case "adjuncts":
        return <AdjunctsTab data={adjunctsData} loading={adjunctsLoading} />;
      case "honest-state":
        return <HonestStateTab data={honestStateData} loading={honestStateLoading} />;
      case "accuracy":
        return <AccuracyTab globalData={accuracyGlobal} userData={accuracyUser} loading={accuracyLoading} />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Performance</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full">
          <TabsTrigger value="overview" className="flex-1">Overview</TabsTrigger>
          <TabsTrigger value="analysis" className="flex-1">Analysis</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4 mt-4">
          <PerformanceSummary
            improvement={summary.improvement}
            change21d={summary.change21d}
            readiness={summary.readiness}
          />
          <FitnessSnapshotTable snapshot={snapshot} />

          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <BarChart3 className="h-4 w-4" /> Projection Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ProjectionHistoryChart
                data={
                  trendsData ??
                  (() => {
                    const baselineSeconds = 21 * 60;
                    const improvement = summary.improvement;
                    return Array.from({ length: 90 }, (_, i) => {
                      const date = new Date(2026, 2, 5);
                      date.setDate(date.getDate() - (89 - i));
                      return {
                        date: date.toISOString().split("T")[0],
                        time: baselineSeconds - i * (improvement / 90),
                      };
                    });
                  })()
                }
                baselineTime={21 * 60}
                rangeData={trendsRangeData ?? undefined}
              />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Baseline Race</p>
                    <p className="text-xs text-muted-foreground">
                      {baseline
                        ? `${EVENT_NAMES[baseline.event] ?? baseline.event} — ${formatTime(baseline.time_seconds)}${baseline.race_date ? ` (${new Date(baseline.race_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })})` : ""}`
                        : "Not set"}
                    </p>
                  </div>
                </div>
                {baseline && <Badge variant="secondary">Active</Badge>}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analysis" className="space-y-3 mt-4">
          {ANALYSIS_SECTIONS.map(({ key, label, icon: Icon }) => (
            <Collapsible
              key={key}
              open={expandedSection === key}
              onOpenChange={(open) => handleSectionToggle(key, open)}
            >
              <Card>
                <CollapsibleTrigger className="w-full text-left">
                  <CardContent className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <p className="text-sm font-medium">{label}</p>
                    </div>
                    <ChevronDown
                      className={`h-4 w-4 text-muted-foreground transition-transform ${
                        expandedSection === key ? "rotate-180" : ""
                      }`}
                    />
                  </CardContent>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="px-4 pb-4 border-t pt-4">
                    {renderAnalysisContent(key)}
                  </div>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}
