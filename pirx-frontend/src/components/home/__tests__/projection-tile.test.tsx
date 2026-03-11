import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProjectionTile } from "../projection-tile";

describe("ProjectionTile model metadata", () => {
  it("renders human-readable model source, confidence, and fallback reason", () => {
    render(
      <ProjectionTile
        event="5000"
        projectedTime="19:50"
        range="19:30 - 20:10"
        improvementSeconds={12}
        twentyOneDayChange={8}
        modelSource="lstm"
        modelConfidence={0.84}
        fallbackReason="fallback_from_lstm_unavailable"
      />
    );

    expect(screen.getByText("LSTM model")).toBeDefined();
    expect(screen.getByText("84% confidence")).toBeDefined();
    expect(screen.getByText("LSTM unavailable, using deterministic projection")).toBeDefined();
  });
});
