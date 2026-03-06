"use client";

import { BottomTabBar } from "@/components/layout/bottom-tab-bar";
import { ChatFAB } from "@/components/layout/chat-fab";
import { TourProvider } from "@/components/tour/tour-provider";
import { ConsentBanner } from "@/components/layout/consent-banner";
import { useNotifications } from "@/hooks/use-notifications";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  useNotifications();

  return (
    <div className="min-h-dvh bg-background pb-20">
      <main className="mx-auto max-w-lg px-4 py-6">{children}</main>
      <ChatFAB />
      <BottomTabBar />
      <TourProvider />
      <ConsentBanner />
    </div>
  );
}
