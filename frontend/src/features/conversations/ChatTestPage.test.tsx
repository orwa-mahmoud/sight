import { describe, it, expect } from "vitest";

describe("ChatTestPage", () => {
  it("module exports ChatTestPage", async () => {
    const mod = await import("./ChatTestPage");
    expect(typeof mod.ChatTestPage).toBe("function");
  });
});
