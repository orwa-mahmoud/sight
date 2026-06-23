import { describe, expect, it } from "vitest";

import { fieldText } from "./cellText";

describe("fieldText", () => {
  it("returns strings unchanged", () => {
    expect(fieldText("hello")).toBe("hello");
    expect(fieldText("")).toBe("");
  });

  it("stringifies numbers, booleans, and bigints", () => {
    expect(fieldText(42)).toBe("42");
    expect(fieldText(0)).toBe("0");
    expect(fieldText(true)).toBe("true");
    expect(fieldText(false)).toBe("false");
    expect(fieldText(10n)).toBe("10");
  });

  it("returns '' for null and undefined", () => {
    expect(fieldText(null)).toBe("");
    expect(fieldText(undefined)).toBe("");
  });

  it("returns '' for objects and arrays (no meaningful text form)", () => {
    expect(fieldText({ a: 1 })).toBe("");
    expect(fieldText([1, 2, 3])).toBe("");
  });
});
