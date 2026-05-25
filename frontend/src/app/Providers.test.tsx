import { describe, it, expect } from "vitest";

describe("Providers", () => {
  it("module exports Providers function", async () => {
    const mod = await import("./Providers");
    expect(typeof mod.Providers).toBe("function");
  });
});
