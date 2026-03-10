"use client";

import { BottomTabBar } from "@/components/layout/bottom-tab-bar";
import { ChatFAB } from "@/components/layout/chat-fab";
import { TourProvider } from "@/components/tour/tour-provider";
import { ConsentBanner } from "@/components/layout/consent-banner";
import { useNotifications } from "@/hooks/use-notifications";
import { motion } from "framer-motion";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  useNotifications();

  return (
    <div className="min-h-dvh bg-background pb-20">
      <motion.main
        className="mx-auto max-w-lg px-4 py-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
      >
        {children}
      </motion.main>
      <ChatFAB />
      <BottomTabBar />
      <TourProvider />
      <ConsentBanner />
    </div>
  );
}
