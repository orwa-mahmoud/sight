import { describe, it, expect } from "vitest";
import { theme } from "./theme";

describe("theme", () => {
  it("has coral as primary color", () => {
    expect(theme.primaryColor).toBe("coral");
  });

  it("defines 10 coral shades", () => {
    expect(theme.colors?.coral).toHaveLength(10);
  });

  it("defines 10 slate shades", () => {
    expect(theme.colors?.slate).toHaveLength(10);
  });

  it("uses md as default radius", () => {
    expect(theme.defaultRadius).toBe("md");
  });
});
