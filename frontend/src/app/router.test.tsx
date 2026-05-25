import { describe, it, expect } from "vitest";

describe("AppRoutes", () => {
  it("module exports AppRoutes function", async () => {
    const mod = await import("./router");
    expect(typeof mod.AppRoutes).toBe("function");
  });
});
