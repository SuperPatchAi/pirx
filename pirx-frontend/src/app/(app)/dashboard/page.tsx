"use client";

import { ProjectionTile } from "@/components/home/projection-tile";
import { EventSwiper } from "@/components/home/event-swiper";
import { DriverStrip } from "@/components/home/driver-strip";
import { QuickMetrics } from "@/components/home/quick-metrics";
import { SyncBanner } from "@/components/home/sync-banner";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <SyncBanner />

      <ProjectionTile
        event="5000"
        projectedTime="19:42"
        range="19:15 – 20:08"
        improvementSeconds={78}
        twentyOneDayChange={5}
      />

      <EventSwiper />

      <DriverStrip />

      <QuickMetrics />
    </div>
  );
}
