import { describe, it, expect } from "vitest";

describe("SettingsPage", () => {
  it("module exports SettingsPage", async () => {
    const mod = await import("./SettingsPage");
    expect(typeof mod.SettingsPage).toBe("function");
  });
});
