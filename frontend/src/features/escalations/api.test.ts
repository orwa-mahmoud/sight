import { describe, it, expect } from "vitest";

describe("escalations API", () => {
  it("exports listQuestions", async () => {
    const mod = await import("./api");
    expect(typeof mod.listQuestions).toBe("function");
  });
  it("exports replyToQuestion", async () => {
    const mod = await import("./api");
    expect(typeof mod.replyToQuestion).toBe("function");
  });
  it("exports closeQuestion", async () => {
    const mod = await import("./api");
    expect(typeof mod.closeQuestion).toBe("function");
  });
});
