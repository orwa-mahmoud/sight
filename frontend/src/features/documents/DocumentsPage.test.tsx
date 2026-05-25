import { describe, it, expect } from "vitest";

describe("DocumentsPage", () => {
  it("module exports DocumentsPage", async () => {
    const mod = await import("./DocumentsPage");
    expect(typeof mod.DocumentsPage).toBe("function");
  });
});
