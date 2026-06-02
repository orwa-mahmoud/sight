import { describe, expect, it } from "vitest";

import { stringifyCellValue } from "./stringify";

describe("stringifyCellValue", () => {
  it("returns empty string for null/undefined", () => {
    expect(stringifyCellValue(null)).toBe("");
    expect(stringifyCellValue(undefined)).toBe("");
  });

  it("returns strings unchanged", () => {
    expect(stringifyCellValue("hello")).toBe("hello");
  });

  it("stringifies numbers, booleans, and bigints", () => {
    expect(stringifyCellValue(42)).toBe("42");
    expect(stringifyCellValue(true)).toBe("true");
    expect(stringifyCellValue(10n)).toBe("10");
  });

  it("JSON-encodes objects instead of '[object Object]'", () => {
    expect(stringifyCellValue({ a: 1 })).toBe('{"a":1}');
    expect(stringifyCellValue([1, 2])).toBe("[1,2]");
  });

  it("renders symbols via toString", () => {
    expect(stringifyCellValue(Symbol("s"))).toBe("Symbol(s)");
  });

  it("returns empty string for functions (not a display value)", () => {
    expect(stringifyCellValue(() => 1)).toBe("");
  });
});
