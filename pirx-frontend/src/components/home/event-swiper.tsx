"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

interface EventCard {
  event: string;
  displayName: string;
  projectedTime: string;
  change: string;
}

const MOCK_EVENTS: EventCard[] = [
  { event: "1500", displayName: "1500m", projectedTime: "5:42", change: "-3s" },
  { event: "3000", displayName: "3K", projectedTime: "12:18", change: "-8s" },
  { event: "5000", displayName: "5K", projectedTime: "20:42", change: "-5s" },
  { event: "10000", displayName: "10K", projectedTime: "43:15", change: "-12s" },
];

export function EventSwiper() {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-muted-foreground">All Events</h3>
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
        {MOCK_EVENTS.map((e) => (
          <Link key={e.event} href={`/event/${e.event}`} className="flex-shrink-0">
            <Card className="w-[140px] hover:border-primary/50 transition-colors">
              <CardContent className="p-3 space-y-2">
                <p className="text-xs text-muted-foreground">{e.displayName}</p>
                <p className="text-xl font-bold tabular-nums">{e.projectedTime}</p>
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
