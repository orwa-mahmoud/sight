import { describe, it, expect } from "vitest";

describe("auth API", () => {
  it("exports login function", async () => {
    const mod = await import("./api");
    expect(typeof mod.login).toBe("function");
  });
  it("exports register function", async () => {
    const mod = await import("./api");
    expect(typeof mod.register).toBe("function");
  });
  it("exports me function", async () => {
    const mod = await import("./api");
    expect(typeof mod.me).toBe("function");
  });
});
