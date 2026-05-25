import { describe, it, expect } from "vitest";

describe("settings API", () => {
  it("exports getSettings", async () => {
    const mod = await import("./api");
    expect(typeof mod.getSettings).toBe("function");
  });
  it("exports updateLLM", async () => {
    const mod = await import("./api");
    expect(typeof mod.updateLLM).toBe("function");
  });
  it("exports updateWhatsApp", async () => {
    const mod = await import("./api");
    expect(typeof mod.updateWhatsApp).toBe("function");
  });
  it("exports updateTelegram", async () => {
    const mod = await import("./api");
    expect(typeof mod.updateTelegram).toBe("function");
  });
  it("exports updateBot", async () => {
    const mod = await import("./api");
    expect(typeof mod.updateBot).toBe("function");
  });
});
