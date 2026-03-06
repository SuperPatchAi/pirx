"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { useTourStore } from "@/stores/tour-store";
import {
  Timer,
  BarChart3,
  Activity,
  Heart,
  MessageCircle,
  ChevronRight,
  X,
  Zap,
} from "lucide-react";

interface SlideData {
  icon: typeof Timer;
  iconBg: string;
  title: string;
  subtitle: string;
  description: string;
}

const SLIDES: SlideData[] = [
  {
    icon: Zap,
    iconBg: "bg-primary/20 text-primary",
    title: "Welcome to PIRX",
    subtitle: "Performance Intelligence Rx",
    description:
      "Your projection-driven running intelligence system. PIRX observes your training, models your performance, and shows you where your fitness actually stands.",
  },
  {
    icon: Timer,
    iconBg: "bg-green-500/20 text-green-500",
    title: "Your Projected Time",
    subtitle: "One number, always current",
    description:
      "This is your central metric \u2014 a projected race time built from your actual training data. It updates with every run and includes a supported range showing the confidence window.",
  },
  {
    icon: BarChart3,
    iconBg: "bg-blue-500/20 text-blue-500",
    title: "5 Structural Drivers",
    subtitle: "What\u2019s actually changing your time",
    description:
      "Aerobic Base, Threshold Density, Speed Exposure, Running Economy, and Load Consistency. Each driver shows its contribution in seconds and whether it\u2019s improving, stable, or declining.",
  },
  {
    icon: Activity,
    iconBg: "bg-amber-500/20 text-amber-500",
    title: "Performance & Physiology",
    subtitle: "Deep-dive into your data",
    description:
      "The Performance tab shows trends, zone analysis, readiness scores, and learning insights. The Physiology tab tracks resting HR, HRV, sleep, and mindset over time.",
  },
  {
    icon: MessageCircle,
    iconBg: "bg-purple-500/20 text-purple-500",
    title: "Chat with PIRX",
    subtitle: "Ask questions, get explanations",
    description:
      "Tap the chat bubble anytime to ask about your training. PIRX can explain your drivers, compare time periods, and give insight into what\u2019s moving your projection.",
  },
];

function DotIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`h-2 rounded-full transition-all duration-300 ${
            i === current
              ? "w-6 bg-primary"
              : i < current
                ? "w-2 bg-primary/50"
                : "w-2 bg-white/30"
          }`}
        />
      ))}
    </div>
  );
}

export function TourSlides() {
  const { currentStep, totalSlides, nextStep, skipTour, goToSpotlight } =
    useTourStore();
  const [direction, setDirection] = useState(0);

  const isLastSlide = currentStep === totalSlides - 1;
  const slide = SLIDES[currentStep];
  const Icon = slide.icon;

  const handleNext = useCallback(() => {
    if (isLastSlide) {
      goToSpotlight();
    } else {
      setDirection(1);
      nextStep();
    }
  }, [isLastSlide, goToSpotlight, nextStep]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "Enter") handleNext();
      if (e.key === "Escape") skipTour();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [handleNext, skipTour]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 backdrop-blur-sm"
    >
      <button
        onClick={skipTour}
        className="absolute top-4 right-4 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white/70 transition-colors hover:bg-white/20 hover:text-white"
        aria-label="Skip tour"
      >
        <X className="h-5 w-5" />
      </button>

      <div className="flex w-full max-w-sm flex-col items-center px-6">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={currentStep}
            custom={direction}
            initial={{ opacity: 0, x: 60 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -60 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="flex w-full flex-col items-center text-center"
          >
            <motion.div
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
              className={`mb-8 flex h-20 w-20 items-center justify-center rounded-2xl ${slide.iconBg}`}
            >
              <Icon className="h-10 w-10" />
            </motion.div>

            <h2 className="mb-2 text-2xl font-bold text-white">
              {slide.title}
            </h2>
            <p className="mb-4 text-sm font-medium text-white/60">
              {slide.subtitle}
            </p>
            <p className="mb-10 text-sm leading-relaxed text-white/80">
              {slide.description}
            </p>
          </motion.div>
        </AnimatePresence>

        <DotIndicator current={currentStep} total={totalSlides} />

        <div className="mt-8 flex w-full gap-3">
          <Button
            variant="ghost"
            onClick={skipTour}
            className="flex-1 text-white/60 hover:text-white hover:bg-white/10"
          >
            Skip
          </Button>
          <Button
            onClick={handleNext}
            className="flex-1"
          >
            {isLastSlide ? (
              "Let me show you"
            ) : (
              <>
                Next <ChevronRight className="ml-1 h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
