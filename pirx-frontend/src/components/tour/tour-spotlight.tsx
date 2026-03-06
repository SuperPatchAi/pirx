"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useTourStore } from "@/stores/tour-store";
import { ChevronRight, X } from "lucide-react";

interface SpotlightStep {
  target: string;
  title: string;
  description: string;
  position: "top" | "bottom";
}

const SPOTLIGHT_STEPS: SpotlightStep[] = [
  {
    target: "projection-tile",
    title: "Your Projected Time",
    description:
      "This is your current projected race time with the supported range. It updates as new training data comes in.",
    position: "bottom",
  },
  {
    target: "event-swiper",
    title: "Event Distances",
    description:
      "Swipe to see projections for different race distances \u2014 1500m, 3K, 5K, and 10K.",
    position: "bottom",
  },
  {
    target: "driver-strip",
    title: "Structural Drivers",
    description:
      "These 5 drivers show what\u2019s improving (or declining) in your training, measured in seconds of contribution.",
    position: "top",
  },
  {
    target: "chat-fab",
    title: "Chat with PIRX",
    description:
      "Tap this button anytime to ask PIRX about your training, drivers, or projections.",
    position: "top",
  },
  {
    target: "tab-bar",
    title: "Navigation",
    description:
      "Switch between your Dashboard, Performance analysis, Physiology tracking, and Settings.",
    position: "top",
  },
];

const PADDING = 8;
const BORDER_RADIUS = 12;

interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

function useTargetRect(targetAttr: string): Rect | null {
  const [rect, setRect] = useState<Rect | null>(null);

  useEffect(() => {
    function measure() {
      const el = document.querySelector(`[data-tour="${targetAttr}"]`);
      if (!el) {
        setRect(null);
        return;
      }
      const r = el.getBoundingClientRect();
      setRect({ x: r.x, y: r.y, width: r.width, height: r.height });
    }

    measure();

    const timer = setTimeout(measure, 100);

    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [targetAttr]);

  return rect;
}

function SpotlightTooltip({
  step,
  rect,
  stepIndex,
  totalSteps,
  onNext,
  onSkip,
}: {
  step: SpotlightStep;
  rect: Rect;
  stepIndex: number;
  totalSteps: number;
  onNext: () => void;
  onSkip: () => void;
}) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const isLast = stepIndex === totalSteps - 1;

  const tooltipStyle: React.CSSProperties = {};
  if (step.position === "bottom") {
    tooltipStyle.top = rect.y + rect.height + PADDING + 12;
    tooltipStyle.left = Math.max(16, Math.min(rect.x, window.innerWidth - 320));
  } else {
    tooltipStyle.bottom = window.innerHeight - rect.y + PADDING + 12;
    tooltipStyle.left = Math.max(16, Math.min(rect.x, window.innerWidth - 320));
  }

  return (
    <motion.div
      ref={tooltipRef}
      initial={{ opacity: 0, y: step.position === "bottom" ? -8 : 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: step.position === "bottom" ? -8 : 8 }}
      transition={{ duration: 0.2 }}
      className="fixed z-[72] w-[calc(100vw-32px)] max-w-[300px] rounded-xl border border-border bg-card p-4 shadow-2xl"
      style={tooltipStyle}
    >
      <div className="mb-1 flex items-center justify-between">
        <h3 className="text-sm font-semibold">{step.title}</h3>
        <span className="text-[10px] text-muted-foreground tabular-nums">
          {stepIndex + 1} of {totalSteps}
        </span>
      </div>
      <p className="mb-4 text-xs leading-relaxed text-muted-foreground">
        {step.description}
      </p>
      <div className="flex items-center justify-between">
        <button
          onClick={onSkip}
          className="text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          Skip
        </button>
        <Button size="sm" onClick={onNext} className="h-8 px-4 text-xs">
          {isLast ? (
            "Done"
          ) : (
            <>
              Next <ChevronRight className="ml-1 h-3 w-3" />
            </>
          )}
        </Button>
      </div>
    </motion.div>
  );
}

export function TourSpotlight() {
  const { currentStep, totalSpotlights, nextStep, skipTour } = useTourStore();
  const step = SPOTLIGHT_STEPS[currentStep];
  const rect = useTargetRect(step.target);

  const handleNext = useCallback(() => {
    nextStep();
  }, [nextStep]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "Enter") handleNext();
      if (e.key === "Escape") skipTour();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [handleNext, skipTour]);

  useEffect(() => {
    if (!rect) return;
    const el = document.querySelector(`[data-tour="${step.target}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [step.target, rect]);

  if (!rect) return null;

  const cutout = {
    x: rect.x - PADDING,
    y: rect.y - PADDING,
    width: rect.width + PADDING * 2,
    height: rect.height + PADDING * 2,
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[70]"
    >
      <button
        onClick={skipTour}
        className="absolute top-4 right-4 z-[73] flex h-10 w-10 items-center justify-center rounded-full bg-black/40 text-white/70 transition-colors hover:bg-black/60 hover:text-white"
        aria-label="Skip tour"
      >
        <X className="h-5 w-5" />
      </button>

      <svg
        className="fixed inset-0 z-[70] h-full w-full"
        style={{ pointerEvents: "none" }}
      >
        <defs>
          <mask id="spotlight-mask">
            <rect width="100%" height="100%" fill="white" />
            <rect
              x={cutout.x}
              y={cutout.y}
              width={cutout.width}
              height={cutout.height}
              rx={BORDER_RADIUS}
              fill="black"
            />
          </mask>
        </defs>
        <rect
          width="100%"
          height="100%"
          fill="rgba(0,0,0,0.6)"
          mask="url(#spotlight-mask)"
        />
      </svg>

      {/* Pulse ring around cutout */}
      <motion.div
        className="fixed z-[71] rounded-xl border-2 border-primary/60"
        style={{
          left: cutout.x - 2,
          top: cutout.y - 2,
          width: cutout.width + 4,
          height: cutout.height + 4,
          pointerEvents: "none",
        }}
        animate={{
          boxShadow: [
            "0 0 0 0px rgba(var(--primary-rgb, 59 130 246) / 0.4)",
            "0 0 0 6px rgba(var(--primary-rgb, 59 130 246) / 0)",
          ],
        }}
        transition={{ duration: 1.5, repeat: Infinity }}
      />

      {/* Click-through hole over the target */}
      <div
        className="fixed z-[71]"
        style={{
          left: cutout.x,
          top: cutout.y,
          width: cutout.width,
          height: cutout.height,
          pointerEvents: "auto",
          cursor: "default",
        }}
        onClick={(e) => e.stopPropagation()}
      />

      {/* Overlay click area to block interaction outside the target */}
      <div
        className="fixed inset-0 z-[70]"
        style={{ pointerEvents: "auto" }}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
      />

      <AnimatePresence mode="wait">
        <SpotlightTooltip
          key={currentStep}
          step={step}
          rect={rect}
          stepIndex={currentStep}
          totalSteps={totalSpotlights}
          onNext={handleNext}
          onSkip={skipTour}
        />
      </AnimatePresence>
    </motion.div>
  );
}
