import { describe, it, expect, beforeEach } from "vitest";
import { useTourStore } from "../tour-store";

const STORAGE_KEY = "pirx-tour-completed";

describe("tour-store", () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY);
    useTourStore.setState({
      isActive: false,
      phase: "slides",
      currentStep: 0,
    });
  });

  it("starts inactive", () => {
    const state = useTourStore.getState();
    expect(state.isActive).toBe(false);
    expect(state.phase).toBe("slides");
    expect(state.currentStep).toBe(0);
  });

  it("startTour activates slides phase at step 0", () => {
    useTourStore.getState().startTour();
    const state = useTourStore.getState();
    expect(state.isActive).toBe(true);
    expect(state.phase).toBe("slides");
    expect(state.currentStep).toBe(0);
  });

  it("nextStep increments within slides phase", () => {
    useTourStore.getState().startTour();
    useTourStore.getState().nextStep();
    expect(useTourStore.getState().currentStep).toBe(1);
    expect(useTourStore.getState().phase).toBe("slides");
  });

  it("transitions from slides to spotlight at end of slides", () => {
    useTourStore.getState().startTour();
    const totalSlides = useTourStore.getState().totalSlides;
    for (let i = 0; i < totalSlides; i++) {
      useTourStore.getState().nextStep();
    }
    expect(useTourStore.getState().phase).toBe("spotlight");
    expect(useTourStore.getState().currentStep).toBe(0);
  });

  it("ends tour at end of spotlight phase", () => {
    useTourStore.getState().startTour();
    // Advance through all slides
    const totalSlides = useTourStore.getState().totalSlides;
    for (let i = 0; i < totalSlides; i++) {
      useTourStore.getState().nextStep();
    }
    // Advance through all spotlights
    const totalSpotlights = useTourStore.getState().totalSpotlights;
    for (let i = 0; i < totalSpotlights; i++) {
      useTourStore.getState().nextStep();
    }
    expect(useTourStore.getState().isActive).toBe(false);
    expect(localStorage.getItem(STORAGE_KEY)).toBe("true");
  });

  it("skipTour ends tour and marks completed", () => {
    useTourStore.getState().startTour();
    useTourStore.getState().skipTour();
    expect(useTourStore.getState().isActive).toBe(false);
    expect(localStorage.getItem(STORAGE_KEY)).toBe("true");
  });

  it("goToSpotlight transitions directly to spotlight phase", () => {
    useTourStore.getState().startTour();
    useTourStore.getState().goToSpotlight();
    expect(useTourStore.getState().phase).toBe("spotlight");
    expect(useTourStore.getState().currentStep).toBe(0);
  });

  it("hasCompleted returns false before tour, true after", () => {
    expect(useTourStore.getState().hasCompleted()).toBe(false);
    useTourStore.getState().startTour();
    useTourStore.getState().endTour();
    expect(useTourStore.getState().hasCompleted()).toBe(true);
  });

  it("resetCompleted clears the localStorage flag", () => {
    useTourStore.getState().startTour();
    useTourStore.getState().endTour();
    expect(useTourStore.getState().hasCompleted()).toBe(true);
    useTourStore.getState().resetCompleted();
    expect(useTourStore.getState().hasCompleted()).toBe(false);
  });

  it("prevStep decrements within current phase", () => {
    useTourStore.getState().startTour();
    useTourStore.getState().nextStep();
    useTourStore.getState().nextStep();
    expect(useTourStore.getState().currentStep).toBe(2);
    useTourStore.getState().prevStep();
    expect(useTourStore.getState().currentStep).toBe(1);
  });

  it("prevStep does not go below 0", () => {
    useTourStore.getState().startTour();
    useTourStore.getState().prevStep();
    expect(useTourStore.getState().currentStep).toBe(0);
  });
});
