import { describe, it, expect } from "vitest";

describe("RegisterPage", () => {
  it("module exports RegisterPage", async () => {
    const mod = await import("./RegisterPage");
    expect(typeof mod.RegisterPage).toBe("function");
  });
});
