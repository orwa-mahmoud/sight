import { describe, it, expect } from "vitest";

describe("ConversationsPage", () => {
  it("module exports ConversationsPage", async () => {
    const mod = await import("./ConversationsPage");
    expect(typeof mod.ConversationsPage).toBe("function");
  });
});
