import { create } from "zustand";

interface DriverData {
  name: string;
  displayName: string;
  contributionSeconds: number;
  score: number;
  trend: "improving" | "stable" | "declining";
}

interface ProjectionState {
  currentEvent: string;
  projectedTimeSeconds: number | null;
  rangeLower: number | null;
  rangeUpper: number | null;
  improvementSeconds: number | null;
  twentyOneDayChange: number | null;
  volatility: number | null;
  lastUpdated: string | null;
  drivers: DriverData[];
  readinessScore: number | null;
  readinessLabel: string | null;
  setCurrentEvent: (event: string) => void;
  setProjection: (data: Partial<ProjectionState>) => void;
  setDrivers: (drivers: DriverData[]) => void;
  setReadiness: (score: number, label: string) => void;
}

export const useProjectionStore = create<ProjectionState>((set) => ({
  currentEvent: "5000",
  projectedTimeSeconds: null,
  rangeLower: null,
  rangeUpper: null,
  improvementSeconds: null,
  twentyOneDayChange: null,
  volatility: null,
  lastUpdated: null,
  drivers: [],
  readinessScore: null,
  readinessLabel: null,
  setCurrentEvent: (event) => set({ currentEvent: event }),
  setProjection: (data) => set((state) => ({ ...state, ...data })),
  setDrivers: (drivers) => set({ drivers }),
  setReadiness: (score, label) =>
    set({ readinessScore: score, readinessLabel: label }),
}));
