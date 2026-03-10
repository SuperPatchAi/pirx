"use client";

import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { CalendarDays } from "lucide-react";

interface EventCard {
  event: string;
  displayName: string;
  projectedTime: string;
  change: string;
}

interface EventSwiperProps {
  apiData?: EventCard[] | null;
  selectedEvent?: string;
  onEventSelect?: (event: string) => void;
}

export function EventSwiper({
  apiData,
  selectedEvent,
  onEventSelect,
}: EventSwiperProps) {
  const events = apiData ?? [];

  if (events.length === 0) {
    return (
      <div className="space-y-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">All Events</h3>
        <EmptyState
          icon={CalendarDays}
          message="No event projections yet"
          submessage="Sync data to see all events"
        />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">All Events</h3>
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
        {events.map((e) => {
          const isSelected = selectedEvent === e.event;
          return (
            <button
              key={e.event}
              className="flex-shrink-0 text-left"
              onClick={() => onEventSelect?.(e.event)}
            >
              <Card
                className={`w-[130px] transition-all ${
                  isSelected
                    ? "border-green-500/60 ring-1 ring-green-500/30 bg-green-500/5"
                    : "border-border/40 hover:border-border"
                }`}
              >
                <CardContent className="p-3 space-y-1.5">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                    {e.displayName}
                  </p>
                  <p className={`text-xl font-bold tabular-nums ${isSelected ? "text-green-500" : ""}`}>
                    {e.projectedTime}
                  </p>
                  <p className={`text-[11px] font-medium tabular-nums ${
                    e.change.startsWith("-") ? "text-green-500" : e.change.startsWith("+") ? "text-red-400" : "text-muted-foreground"
                  }`}>
                    {e.change}
                  </p>
                </CardContent>
              </Card>
            </button>
          );
        })}
      </div>
    </div>
  );
}
