"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

/* ────────────────────────────────────────────────────────────
   Types
   ──────────────────────────────────────────────────────────── */

interface Activity {
  activity_id?: string;
  timestamp: string;
  activity_type?: string;
  distance_meters?: number;
  duration_seconds?: number;
  avg_hr?: number;
  avg_pace_sec_per_km?: number;
}

interface ActivitiesResponse {
  activities: Activity[];
}

/* ────────────────────────────────────────────────────────────
   Helpers
   ──────────────────────────────────────────────────────────── */

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function toDateKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function getCellBg(activityType: string | undefined): string {
  if (!activityType) return "bg-secondary/30";
  switch (activityType) {
    case "easy":
    case "long_run":
      return "bg-green-500/25";
    case "threshold":
      return "bg-green-500/50";
    case "interval":
    case "race":
      return "bg-green-500";
    default:
      return "bg-secondary/50";
  }
}

function formatPace(secPerKm: number | null | undefined): string {
  if (secPerKm == null || secPerKm <= 0) return "—";
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return `${m}:${s.toString().padStart(2, "0")}/km`;
}

function formatDuration(sec: number | null | undefined): string {
  if (sec == null || sec <= 0) return "—";
  const m = Math.floor(sec / 60);
  const h = Math.floor(m / 60);
  const mins = m % 60;
  if (h > 0) return `${h}h ${mins}m`;
  return `${mins}m`;
}

function formatActivityType(type: string | undefined): string {
  if (!type) return "Run";
  const map: Record<string, string> = {
    easy: "Easy Run",
    threshold: "Tempo / Threshold",
    interval: "Interval",
    race: "Race",
    long_run: "Long Run",
  };
  return map[type] ?? type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ────────────────────────────────────────────────────────────
   Calendar grid
   ──────────────────────────────────────────────────────────── */

function getCalendarDays(year: number, month: number): { date: Date; dayNum: number; isCurrentMonth: boolean }[] {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const startDow = (first.getDay() + 6) % 7; // Monday = 0
  const daysInMonth = last.getDate();

  const result: { date: Date; dayNum: number; isCurrentMonth: boolean }[] = [];

  // Leading days from previous month
  const prevMonthLast = new Date(year, month, 0);
  const prevMonthDays = prevMonthLast.getDate();
  for (let i = 0; i < startDow; i++) {
    const d = prevMonthDays - startDow + 1 + i;
    result.push({
      date: new Date(year, month - 1, d),
      dayNum: d,
      isCurrentMonth: false,
    });
  }

  // Current month
  for (let d = 1; d <= daysInMonth; d++) {
    result.push({
      date: new Date(year, month, d),
      dayNum: d,
      isCurrentMonth: true,
    });
  }

  // Trailing days to complete last row
  const total = result.length;
  const remainder = total % 7;
  const trailing = remainder === 0 ? 0 : 7 - remainder;
  for (let d = 1; d <= trailing; d++) {
    result.push({
      date: new Date(year, month + 1, d),
      dayNum: d,
      isCurrentMonth: false,
    });
  }

  return result;
}

/* ────────────────────────────────────────────────────────────
   Page
   ──────────────────────────────────────────────────────────── */

export default function CalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(() => new Date());
  const [activities, setActivities] = useState<Activity[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);

  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const monthName = currentMonth.toLocaleString("default", { month: "long" });

  const loadActivities = useCallback(async () => {
    setLoading(true);
    const first = new Date(year, month, 1);
    const last = new Date(year, month + 1, 0);
    const fromStr = toDateKey(first);
    const toStr = toDateKey(last);
    try {
      const data = (await apiFetch(
        `/activities?from=${fromStr}&to=${toStr}`
      )) as ActivitiesResponse;
      setActivities(data.activities ?? []);
    } catch {
      setActivities([]);
    } finally {
      setLoading(false);
    }
  }, [year, month]);

  useEffect(() => {
    loadActivities();
  }, [loadActivities]);

  const activitiesByDate = activities.reduce<Record<string, Activity[]>>((acc, a) => {
    const key = (a.timestamp || "").slice(0, 10);
    if (!key) return acc;
    if (!acc[key]) acc[key] = [];
    acc[key].push(a);
    return acc;
  }, {});

  const goPrev = () => setCurrentMonth((d) => new Date(d.getFullYear(), d.getMonth() - 1));
  const goNext = () => setCurrentMonth((d) => new Date(d.getFullYear(), d.getMonth() + 1));

  const calendarDays = getCalendarDays(year, month);

  // Stats for current month
  const totalKm = activities.reduce((sum, a) => sum + (a.distance_meters ?? 0) / 1000, 0);
  const sessions = activities.length;
  const paces = activities
    .filter((a) => a.avg_pace_sec_per_km != null && a.avg_pace_sec_per_km > 0)
    .map((a) => a.avg_pace_sec_per_km!);
  const avgPace = paces.length > 0 ? paces.reduce((a, b) => a + b, 0) / paces.length : null;

  const selectedKey = selectedDate ? toDateKey(selectedDate) : null;
  const selectedActivities = selectedKey ? activitiesByDate[selectedKey] ?? [] : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-bold tracking-tight">
          Activity <span className="text-green-500">Calendar</span>
        </h1>
        <div className="mt-4 flex items-center justify-between">
          <button
            type="button"
            onClick={goPrev}
            className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            aria-label="Previous month"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold uppercase tracking-widest text-foreground">
            {monthName} {year}
          </span>
          <button
            type="button"
            onClick={goNext}
            className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            aria-label="Next month"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </header>

      {/* Calendar grid */}
      <div className="space-y-2">
        <div className="grid grid-cols-7 gap-1">
          {DAYS.map((d) => (
            <div
              key={d}
              className="text-center text-[10px] font-medium uppercase tracking-widest text-muted-foreground"
            >
              {d.charAt(0)}
            </div>
          ))}
        </div>
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-green-500" />
          </div>
        ) : (
          <div className="grid grid-cols-7 gap-1">
            {calendarDays.map(({ date, dayNum, isCurrentMonth }, idx) => {
              const key = toDateKey(date);
              const dayActivities = activitiesByDate[key] ?? [];
              const primary = dayActivities[0];
              const bg = primary ? getCellBg(primary.activity_type) : "bg-secondary/30";
              const isSelected = selectedKey === key;
              return (
                <button
                  key={`cell-${idx}`}
                  type="button"
                  onClick={() => setSelectedDate(date)}
                  className={`h-10 w-10 rounded-lg flex items-center justify-center text-xs font-medium tabular-nums transition-colors
                    ${bg}
                    ${!isCurrentMonth ? "opacity-30" : ""}
                    ${isSelected ? "ring-2 ring-green-500 ring-offset-2 ring-offset-background" : "hover:ring-2 hover:ring-green-500/50"}
                  `}
                >
                  {dayNum}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2">
        <Card className="border-border/40">
          <CardContent className="p-3 text-center space-y-0.5">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              Total Km
            </p>
            <p className="text-xl font-bold tabular-nums text-green-500">
              {totalKm.toFixed(1)}
              <span className="text-xs font-normal text-muted-foreground ml-0.5">km</span>
            </p>
          </CardContent>
        </Card>
        <Card className="border-border/40">
          <CardContent className="p-3 text-center space-y-0.5">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              Sessions
            </p>
            <p className="text-xl font-bold tabular-nums text-green-500">{sessions}</p>
          </CardContent>
        </Card>
        <Card className="border-border/40">
          <CardContent className="p-3 text-center space-y-0.5">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              Avg Pace
            </p>
            <p className="text-xl font-bold tabular-nums text-green-500">
              {avgPace != null ? formatPace(avgPace) : "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Day detail */}
      {selectedDate && (
        <Card className="border-border/40">
          <CardContent className="p-4">
            <h3 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-3">
              {selectedDate.toLocaleDateString("default", {
                weekday: "long",
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </h3>
            {selectedActivities.length === 0 ? (
              <p className="text-muted-foreground">Rest day</p>
            ) : (
              <div className="space-y-3">
                {selectedActivities.map((a, i) => (
                  <div
                    key={a.activity_id ?? i}
                    className="flex flex-wrap gap-x-4 gap-y-1 text-sm"
                  >
                    <span className="font-medium text-foreground">
                      {formatActivityType(a.activity_type)}
                    </span>
                    <span className="text-muted-foreground">
                      {(a.distance_meters ?? 0) / 1000} km
                    </span>
                    <span className="text-muted-foreground">
                      {formatDuration(a.duration_seconds)}
                    </span>
                    <span className="text-muted-foreground">
                      {formatPace(a.avg_pace_sec_per_km)}
                    </span>
                    {a.avg_hr != null && (
                      <span className="text-muted-foreground">{a.avg_hr} bpm</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
