"use client";

import { AnimatePresence } from "framer-motion";
import { useTourStore } from "@/stores/tour-store";
import { TourSlides } from "./tour-slides";
import { TourSpotlight } from "./tour-spotlight";

export function TourProvider() {
  const isActive = useTourStore((s) => s.isActive);
  const phase = useTourStore((s) => s.phase);

  return (
    <AnimatePresence>
      {isActive && phase === "slides" && <TourSlides key="tour-slides" />}
      {isActive && phase === "spotlight" && (
        <TourSpotlight key="tour-spotlight" />
      )}
    </AnimatePresence>
  );
}
