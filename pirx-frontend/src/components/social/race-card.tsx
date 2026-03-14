"use client";

import { Card, CardContent } from "@/components/ui/card";

interface DriverContribution {
  name: string;
  display_name: string;
  contribution_seconds: number;
}

interface RaceCardProps {
  event: string;
  eventDisplay: string;
  projectedTime: string;
  supportedRange: string;
  improvementSeconds: number;
  twentyOneDayChange: number;
  driverContributions: DriverContribution[];
  percentile?: number | null;
  userName?: string;
}

export function RaceCard({
  eventDisplay,
  projectedTime,
  supportedRange,
  improvementSeconds,
  twentyOneDayChange,
  driverContributions,
  percentile,
  userName,
}: RaceCardProps) {
  const maxContrib = Math.max(
    ...driverContributions.map((d) => Math.abs(d.contribution_seconds)),
    1,
  );

  return (
    <div
      id="pirx-race-card"
      className="w-[360px] bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900 rounded-2xl p-6 space-y-4 border border-zinc-700/50"
    >
      <div className="flex items-center justify-between">
        <div className="text-xs font-bold tracking-widest text-primary uppercase">
          PIRX
        </div>
        <div className="text-xs text-zinc-400">{eventDisplay}</div>
      </div>

      <div className="space-y-1">
        <p className="text-xs text-zinc-400">Projected Time</p>
        <p className="text-5xl font-bold tabular-nums tracking-tight text-white">
          {projectedTime}
        </p>
        <p className="text-xs text-zinc-500">
          Supported Range: {supportedRange}
        </p>
      </div>

      <div className="flex gap-4">
        <div>
          <p className="text-xs text-zinc-400">Improvement</p>
          <p className="text-sm font-semibold text-primary">
            {improvementSeconds > 0 ? "-" : "+"}
            {Math.abs(improvementSeconds)}s
          </p>
        </div>
        <div>
          <p className="text-xs text-zinc-400">21-Day Change</p>
          <p className="text-sm font-semibold text-primary">
            {twentyOneDayChange > 0 ? "-" : "+"}
            {Math.abs(twentyOneDayChange)}s
          </p>
        </div>
        {percentile != null && (
          <div>
            <p className="text-xs text-zinc-400">Cohort</p>
            <p className="text-sm font-semibold text-blue-400">
              Top {100 - percentile}%
            </p>
          </div>
        )}
      </div>

      <div className="space-y-1.5">
        <p className="text-[10px] text-zinc-500 uppercase tracking-wider">
          Driver Breakdown
        </p>
        {driverContributions.map((d) => {
          const pct = Math.min(
            100,
            (Math.abs(d.contribution_seconds) / maxContrib) * 100,
          );
          return (
            <div key={d.name} className="flex items-center gap-2">
              <span className="text-[10px] text-zinc-400 w-20 truncate">
                {d.display_name}
              </span>
              <div className="flex-1 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[10px] text-zinc-400 tabular-nums w-10 text-right">
                -{Math.abs(d.contribution_seconds)}s
              </span>
            </div>
          );
        })}
      </div>

      {userName && (
        <div className="pt-2 border-t border-zinc-700/50">
          <p className="text-[10px] text-zinc-500">{userName} · pirx.app</p>
        </div>
      )}
    </div>
  );
}
