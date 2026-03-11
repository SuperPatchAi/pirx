import { describe, expect, it } from "vitest";
import { mapEntriesToTrend, mapCustomFieldTrend } from "../page";

describe("physiology trend mappers", () => {
  it("maps timestamp-based standard metrics", () => {
    const points = mapEntriesToTrend(
      [
        { timestamp: "2026-03-02T00:00:00Z", resting_hr: 49 },
        { timestamp: "2026-03-01T00:00:00Z", resting_hr: 51 },
      ],
      "resting_hr",
    );
    expect(points[0]).toEqual({ date: "2026-03-01T00:00:00Z", value: 51 });
    expect(points[1]).toEqual({ date: "2026-03-02T00:00:00Z", value: 49 });
  });

  it("maps custom body fields", () => {
    const points = mapCustomFieldTrend(
      [
        { timestamp: "2026-03-01T00:00:00Z", custom_fields: { weight_kg: 70.4 } },
        { timestamp: "2026-03-02T00:00:00Z", custom_fields: { weight_kg: 70.0 } },
      ],
      "weight_kg",
    );
    expect(points).toHaveLength(2);
    expect(points[0].value).toBe(70.4);
    expect(points[1].value).toBe(70);
  });
});
