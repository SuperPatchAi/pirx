"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BottomTabBar } from "@/components/layout/bottom-tab-bar";
import { ChatFAB } from "@/components/layout/chat-fab";
import { TourProvider } from "@/components/tour/tour-provider";
import { ConsentBanner } from "@/components/layout/consent-banner";
import { useNotifications } from "@/hooks/use-notifications";
import { apiFetch } from "@/lib/api";
import { motion } from "framer-motion";

function useOnboardingGate() {
  const pathname = usePathname();
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (pathname.startsWith("/onboarding")) {
      setChecked(true);
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const data = await apiFetch("/account/onboarding-status");
        if (!cancelled && !data.onboarding_completed) {
          router.replace("/onboarding/1");
          return;
        }
      } catch {
        // API unreachable — let user through rather than blocking
      }
      if (!cancelled) setChecked(true);
    })();
    return () => { cancelled = true; };
  }, [pathname, router]);

  return checked;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  useNotifications();
  const ready = useOnboardingGate();

  if (!ready) return null;

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
