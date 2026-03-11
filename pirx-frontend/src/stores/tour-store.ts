import { create } from "zustand";

const STORAGE_KEY_PREFIX = "pirx-tour-completed";
function storageKey(userId?: string) {
  return userId ? `${STORAGE_KEY_PREFIX}-${userId}` : STORAGE_KEY_PREFIX;
}

type TourPhase = "slides" | "spotlight";

interface TourState {
  isActive: boolean;
  phase: TourPhase;
  currentStep: number;
  totalSlides: number;
  totalSpotlights: number;
  startTour: () => void;
  endTour: (userId?: string) => void;
  nextStep: () => void;
  prevStep: () => void;
  skipTour: () => void;
  goToSpotlight: () => void;
  hasCompleted: (userId?: string) => boolean;
  resetCompleted: (userId?: string) => void;
}

export const useTourStore = create<TourState>((set, get) => ({
  isActive: false,
  phase: "slides",
  currentStep: 0,
  totalSlides: 5,
  totalSpotlights: 5,

  startTour: () =>
    set({ isActive: true, phase: "slides", currentStep: 0 }),

  endTour: (userId?: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem(storageKey(userId), "true");
    }
    set({ isActive: false, phase: "slides", currentStep: 0 });
  },

  nextStep: () => {
    const { phase, currentStep, totalSlides, totalSpotlights } = get();
    if (phase === "slides") {
      if (currentStep < totalSlides - 1) {
        set({ currentStep: currentStep + 1 });
      } else {
        set({ phase: "spotlight", currentStep: 0 });
      }
    } else {
      if (currentStep < totalSpotlights - 1) {
        set({ currentStep: currentStep + 1 });
      } else {
        get().endTour();
      }
    }
  },

  prevStep: () => {
    const { currentStep } = get();
    if (currentStep > 0) {
      set({ currentStep: currentStep - 1 });
    }
  },

  skipTour: () => {
    get().endTour();
  },

  goToSpotlight: () => {
    set({ phase: "spotlight", currentStep: 0 });
  },

  hasCompleted: (userId?: string) => {
    if (typeof window === "undefined") return true;
    return localStorage.getItem(storageKey(userId)) === "true";
  },

  resetCompleted: (userId?: string) => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(storageKey(userId));
    }
  },
}));
