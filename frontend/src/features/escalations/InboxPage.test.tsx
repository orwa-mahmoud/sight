import { describe, it, expect } from "vitest";

describe("InboxPage", () => {
  it("module exports InboxPage", async () => {
    const mod = await import("./InboxPage");
    expect(typeof mod.InboxPage).toBe("function");
  });
});
