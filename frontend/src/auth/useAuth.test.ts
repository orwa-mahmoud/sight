import { describe, it, expect } from "vitest";

describe("useAuth hook", () => {
  it("exports useAuth function", async () => {
    const mod = await import("./useAuth");
    expect(typeof mod.useAuth).toBe("function");
  });
});
