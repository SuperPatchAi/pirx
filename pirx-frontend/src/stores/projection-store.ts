import { create } from "zustand";

interface ProjectionState {
  currentEvent: string;
  projectedTimeSeconds: number | null;
  rangeLower: number | null;
  rangeUpper: number | null;
  improvementSeconds: number | null;
  twentyOneDayChange: number | null;
  drivers: Record<string, number>;
  setCurrentEvent: (event: string) => void;
  setProjection: (data: Partial<ProjectionState>) => void;
}

export const useProjectionStore = create<ProjectionState>((set) => ({
  currentEvent: "3000",
  projectedTimeSeconds: null,
  rangeLower: null,
  rangeUpper: null,
  improvementSeconds: null,
  twentyOneDayChange: null,
  drivers: {},
  setCurrentEvent: (event) => set({ currentEvent: event }),
  setProjection: (data) => set((state) => ({ ...state, ...data })),
}));
