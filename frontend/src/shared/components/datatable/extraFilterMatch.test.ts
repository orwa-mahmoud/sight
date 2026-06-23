import { describe, expect, it } from "vitest";

import { matchesExtraFilters } from "./extraFilterMatch";

interface Row {
  status: string;
  name: string;
}

const row: Row = { status: "active", name: "Alpha" };

describe("matchesExtraFilters", () => {
  it("matches when a filter key is unset, empty, or an empty array", () => {
    expect(matchesExtraFilters(row, {})).toBe(true);
    expect(matchesExtraFilters(row, { status: "" })).toBe(true);
    expect(matchesExtraFilters(row, { status: undefined })).toBe(true);
    expect(matchesExtraFilters(row, { status: [] })).toBe(true);
  });

  it("matches a string filter case-insensitively", () => {
    expect(matchesExtraFilters(row, { status: "ACTIVE" })).toBe(true);
    expect(matchesExtraFilters(row, { status: "inactive" })).toBe(false);
  });

  it("matches when the field is one of an array filter's values", () => {
    expect(matchesExtraFilters(row, { status: ["active", "pending"] })).toBe(true);
    expect(matchesExtraFilters(row, { status: ["closed", "pending"] })).toBe(false);
  });

  it("requires every set filter key to match", () => {
    expect(matchesExtraFilters(row, { status: "active", name: "alpha" })).toBe(true);
    expect(matchesExtraFilters(row, { status: "active", name: "beta" })).toBe(false);
  });

  it("treats a non-object row as having no field text", () => {
    const notARow = null as unknown as Row;
    expect(matchesExtraFilters(notARow, {})).toBe(true);
    expect(matchesExtraFilters(notARow, { status: "active" })).toBe(false);
  });
});
