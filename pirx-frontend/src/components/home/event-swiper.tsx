"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import Link from "next/link";
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
        <h3 className="text-sm font-medium text-muted-foreground">All Events</h3>
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
      <h3 className="text-sm font-medium text-muted-foreground">All Events</h3>
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
        {events.map((e) => (
          <Link
            key={e.event}
            href={`/event/${e.event}`}
            className="flex-shrink-0"
            onClick={(ev) => {
              if (onEventSelect) {
                ev.preventDefault();
                onEventSelect(e.event);
              }
            }}
          >
            <Card
              className={`w-[140px] transition-colors ${
                selectedEvent === e.event
                  ? "border-primary ring-1 ring-primary/40"
                  : "hover:border-primary/50"
              }`}
            >
              <CardContent className="p-3 space-y-2">
                <p className="text-xs text-muted-foreground">{e.displayName}</p>
                <p className="text-xl font-bold tabular-nums">
                  {e.projectedTime}
                </p>
                <Badge variant="secondary" className="text-xs">
                  {e.change}
                </Badge>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
