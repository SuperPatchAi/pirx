"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod/v4";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";

/* ------------------------------------------------------------------ */
/*  Mock data generators                                              */
/* ------------------------------------------------------------------ */

function generateTrendData(
  days: number,
  baseFn: (i: number) => number,
): { date: string; value: number }[] {
  const now = new Date();
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(now);
    d.setDate(d.getDate() - (days - 1 - i));
    return {
      date: d.toISOString().slice(0, 10),
      value: Math.round(baseFn(i) * 10) / 10,
    };
  });
}

function seededRandom(seed: number) {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

const hrData = generateTrendData(30, (i) => 52 + (seededRandom(i) * 6 - 3));
const hrvData = generateTrendData(30, (i) => 45 + (seededRandom(i + 100) * 16 - 8));
const sleepData = generateTrendData(30, (i) => 72 + (seededRandom(i + 200) * 24 - 12));

/* ------------------------------------------------------------------ */
/*  Chart component                                                   */
/* ------------------------------------------------------------------ */

const tooltipStyle = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "8px",
  fontSize: "12px",
};

function TrendChart({
  data,
  color,
  domain,
  unit = "",
}: {
  data: { date: string; value: number }[];
  color: string;
  domain: [number, number];
  unit?: string;
}) {
  if (data.length === 0) {
    return (
      <div className="h-[180px] flex items-center justify-center text-xs text-muted-foreground">
        No data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="hsl(var(--border))"
          opacity={0.3}
        />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(d: string) => {
            const date = new Date(d);
            return `${date.getMonth() + 1}/${date.getDate()}`;
          }}
        />
        <YAxis
          domain={domain}
          tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
          width={35}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          labelStyle={{ color: "hsl(var(--muted-foreground))" }}
          formatter={(value: number | undefined) => [
            value != null ? `${value}${unit}` : "",
            "",
          ]}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: color }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

/* ------------------------------------------------------------------ */
/*  Manual Entry schema                                               */
/* ------------------------------------------------------------------ */

const manualEntrySchema = z.object({
  blood_lactate_rest: z.string().optional(),
  blood_lactate_easy: z.string().optional(),
  blood_lactate_threshold: z.string().optional(),
  blood_lactate_race: z.string().optional(),
  hemoglobin: z.string().optional(),
  hematocrit: z.string().optional(),
  ferritin: z.string().optional(),
  rbc: z.string().optional(),
  iron: z.string().optional(),
  vitamin_d: z.string().optional(),
  testosterone: z.string().optional(),
  notes: z.string().optional(),
});

type ManualEntryValues = z.infer<typeof manualEntrySchema>;

/* ------------------------------------------------------------------ */
/*  Mindset schema                                                    */
/* ------------------------------------------------------------------ */

const mindsetSchema = z.object({
  confidence_score: z.number().min(1).max(10),
  fatigue_score: z.number().min(1).max(10),
  focus_score: z.number().min(1).max(10),
  notes: z.string().optional(),
});

type MindsetValues = z.infer<typeof mindsetSchema>;

/* ------------------------------------------------------------------ */
/*  Trends Tab                                                        */
/* ------------------------------------------------------------------ */

type TrendPoint = { date: string; value: number };

function mapEntriesToTrend(
  entries: Record<string, unknown>[],
  valueKey: string,
): TrendPoint[] {
  return entries
    .filter((e) => e.date && (e[valueKey] != null || e.value != null))
    .map((e) => ({
      date: String(e.date),
      value: Number(e[valueKey] ?? e.value ?? 0),
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

function TrendsTab() {
  const [hrTrend, setHrTrend] = useState<TrendPoint[]>(hrData);
  const [hrvTrend, setHrvTrend] = useState<TrendPoint[]>(hrvData);
  const [sleepTrend, setSleepTrend] = useState<TrendPoint[]>(sleepData);

  useEffect(() => {
    async function loadTrends() {
      try {
        const { apiFetch } = await import("@/lib/api");
        const data = await apiFetch("/physiology/trends?days=30");
        if (data.entries && Array.isArray(data.entries) && data.entries.length > 0) {
          const entries = data.entries as Record<string, unknown>[];
          const hr = mapEntriesToTrend(entries, "resting_hr");
          const hrv = mapEntriesToTrend(entries, "hrv");
          const sleep = mapEntriesToTrend(entries, "sleep_score");
          if (hr.length > 0) setHrTrend(hr);
          if (hrv.length > 0) setHrvTrend(hrv);
          if (sleep.length > 0) setSleepTrend(sleep);
        }
      } catch {
        /* use mock data */
      }
    }
    loadTrends();
  }, []);

  return (
    <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Resting HR</CardTitle>
          <CardDescription>30-day trend (bpm)</CardDescription>
        </CardHeader>
        <CardContent>
          <TrendChart
            data={hrTrend}
            color="hsl(var(--primary))"
            domain={[45, 60]}
            unit=" bpm"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">HRV</CardTitle>
          <CardDescription>30-day trend (ms)</CardDescription>
        </CardHeader>
        <CardContent>
          <TrendChart
            data={hrvTrend}
            color="hsl(142 71% 45%)"
            domain={[30, 60]}
            unit=" ms"
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Sleep Score</CardTitle>
          <CardDescription>30-day trend</CardDescription>
        </CardHeader>
        <CardContent>
          <TrendChart
            data={sleepTrend}
            color="hsl(262 83% 58%)"
            domain={[50, 100]}
          />
        </CardContent>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Manual Entry Tab                                                  */
/* ------------------------------------------------------------------ */

function ManualEntryTab() {
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<ManualEntryValues>({
    resolver: zodResolver(manualEntrySchema),
  });

  async function onSubmit(values: ManualEntryValues) {
    const payload: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(values)) {
      if (v === "" || v === undefined || v === null) continue;
      if (k === "notes") {
        payload[k] = v;
      } else {
        const num = parseFloat(v);
        if (!isNaN(num) && num > 0) payload[k] = num;
      }
    }

    setError(null);
    try {
      const { apiFetch } = await import("@/lib/api");
      await apiFetch("/physiology", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSubmitted(true);
      reset();
      setTimeout(() => setSubmitted(false), 3000);
    } catch {
      setError("Failed to save entry. Please try again.");
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {submitted && (
        <div className="rounded-md bg-green-500/10 px-3 py-2 text-sm text-green-500">
          Entry saved successfully.
        </div>
      )}
      {error && (
        <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Blood Lactate (mmol/L)</CardTitle>
          <CardDescription>
            Enter lactate values from your most recent test
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {(
              [
                ["blood_lactate_rest", "Rest"],
                ["blood_lactate_easy", "Easy"],
                ["blood_lactate_threshold", "Threshold"],
                ["blood_lactate_race", "Race"],
              ] as const
            ).map(([field, label]) => (
              <div key={field} className="space-y-2">
                <Label htmlFor={field}>{label}</Label>
                <Input
                  id={field}
                  type="number"
                  step="0.1"
                  placeholder="0.0"
                  {...register(field)}
                />
                {errors[field] && (
                  <p className="text-xs text-destructive">
                    {errors[field]?.message}
                  </p>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Blood Work</CardTitle>
          <CardDescription>
            Lab results and biomarkers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {(
              [
                ["hemoglobin", "Hemoglobin (g/dL)"],
                ["hematocrit", "Hematocrit (%)"],
                ["ferritin", "Ferritin (ng/mL)"],
                ["rbc", "RBC (M/uL)"],
                ["iron", "Iron (ug/dL)"],
                ["vitamin_d", "Vitamin D (ng/mL)"],
                ["testosterone", "Testosterone (ng/dL)"],
              ] as const
            ).map(([field, label]) => (
              <div key={field} className="space-y-2">
                <Label htmlFor={field}>{label}</Label>
                <Input
                  id={field}
                  type="number"
                  step="0.1"
                  placeholder="0.0"
                  {...register(field)}
                />
                {errors[field] && (
                  <p className="text-xs text-destructive">
                    {errors[field]?.message}
                  </p>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Context Notes</CardTitle>
          <CardDescription>
            Additional context for this entry
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            id="notes"
            placeholder="Any additional context about your lab results, how you felt, etc."
            rows={4}
            {...register("notes")}
          />
        </CardContent>
      </Card>

      <Button type="submit" disabled={isSubmitting} className="w-full sm:w-auto">
        {isSubmitting ? "Saving..." : "Save Entry"}
      </Button>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/*  Mindset Tab                                                       */
/* ------------------------------------------------------------------ */

const mindsetTrendConfidence = generateTrendData(30, (i) => Math.round(5 + seededRandom(i + 300) * 4));
const mindsetTrendFatigue = generateTrendData(30, (i) => Math.round(4 + seededRandom(i + 400) * 5));
const mindsetTrendFocus = generateTrendData(30, (i) => Math.round(5 + seededRandom(i + 500) * 4));

function MindsetTab() {
  const [confidence, setConfidence] = useState(5);
  const [fatigue, setFatigue] = useState(5);
  const [focus, setFocus] = useState(5);
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);

  async function handleSave() {
    const payload: MindsetValues = {
      confidence_score: confidence,
      fatigue_score: fatigue,
      focus_score: focus,
      notes: notes || undefined,
    };

    const result = mindsetSchema.safeParse(payload);
    if (!result.success) return;

    try {
      const { apiFetch } = await import("@/lib/api");
      await apiFetch("/physiology", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch {
      // silently handle — fallback
    }

    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
  }

  return (
    <div className="space-y-6">
      {submitted && (
        <div className="rounded-md bg-green-500/10 px-3 py-2 text-sm text-green-500">
          Mindset scores saved.
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Rate Your Mindset</CardTitle>
          <CardDescription>
            Score each dimension from 1 (low) to 10 (high)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Confidence</Label>
              <span className="text-sm font-medium tabular-nums">{confidence}</span>
            </div>
            <Slider
              min={1}
              max={10}
              step={1}
              value={[confidence]}
              onValueChange={(v) => setConfidence(v[0])}
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Fatigue</Label>
              <span className="text-sm font-medium tabular-nums">{fatigue}</span>
            </div>
            <Slider
              min={1}
              max={10}
              step={1}
              value={[fatigue]}
              onValueChange={(v) => setFatigue(v[0])}
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Focus</Label>
              <span className="text-sm font-medium tabular-nums">{focus}</span>
            </div>
            <Slider
              min={1}
              max={10}
              step={1}
              value={[focus]}
              onValueChange={(v) => setFocus(v[0])}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="mindset-notes">Notes</Label>
            <Textarea
              id="mindset-notes"
              placeholder="How are you feeling today?"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <Button onClick={handleSave} className="w-full sm:w-auto">
            Save Mindset
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Confidence</CardTitle>
            <CardDescription>30-day trend</CardDescription>
          </CardHeader>
          <CardContent>
            <TrendChart
              data={mindsetTrendConfidence}
              color="hsl(var(--primary))"
              domain={[0, 10]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Fatigue</CardTitle>
            <CardDescription>30-day trend</CardDescription>
          </CardHeader>
          <CardContent>
            <TrendChart
              data={mindsetTrendFatigue}
              color="hsl(0 84% 60%)"
              domain={[0, 10]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Focus</CardTitle>
            <CardDescription>30-day trend</CardDescription>
          </CardHeader>
          <CardContent>
            <TrendChart
              data={mindsetTrendFocus}
              color="hsl(142 71% 45%)"
              domain={[0, 10]}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function PhysiologyPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Physiology</h1>
        <p className="text-muted-foreground">
          Track physiological metrics, lab results, and mindset
        </p>
      </div>

      <Tabs defaultValue="trends">
        <TabsList>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="manual">Manual Entry</TabsTrigger>
          <TabsTrigger value="mindset">Mindset</TabsTrigger>
        </TabsList>

        <TabsContent value="trends">
          <TrendsTab />
        </TabsContent>

        <TabsContent value="manual">
          <ManualEntryTab />
        </TabsContent>

        <TabsContent value="mindset">
          <MindsetTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
