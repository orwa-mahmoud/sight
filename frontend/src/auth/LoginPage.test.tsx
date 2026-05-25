import { describe, it, expect } from "vitest";

describe("LoginPage", () => {
  it("module exports LoginPage", async () => {
    const mod = await import("./LoginPage");
    expect(typeof mod.LoginPage).toBe("function");
  });
});
