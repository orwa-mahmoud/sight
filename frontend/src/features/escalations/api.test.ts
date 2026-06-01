import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@core/api/client", () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

import { api } from "@core/api/client";
import { listQuestions, replyToQuestion, closeQuestion } from "./api";

describe("escalations API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listQuestions fetches /api/v1/questions without status", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    const result = await listQuestions();
    expect(api.get).toHaveBeenCalledWith("/api/v1/questions", { params: undefined });
    expect(result).toEqual([]);
  });

  it("listQuestions passes status param when provided", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [{ id: "q1" }] });
    await listQuestions("submitted");
    expect(api.get).toHaveBeenCalledWith("/api/v1/questions", { params: { status: "submitted" } });
  });

  it("replyToQuestion posts to correct endpoint", async () => {
    const updated = { id: "q1", status: "resolved", owner_reply: "Done" };
    vi.mocked(api.post).mockResolvedValue({ data: updated });
    const result = await replyToQuestion("q1", "Done");
    expect(api.post).toHaveBeenCalledWith("/api/v1/questions/q1/reply", { reply: "Done" });
    expect(result).toEqual(updated);
  });

  it("closeQuestion posts to correct endpoint", async () => {
    const updated = { id: "q2", status: "closed" };
    vi.mocked(api.post).mockResolvedValue({ data: updated });
    const result = await closeQuestion("q2");
    expect(api.post).toHaveBeenCalledWith("/api/v1/questions/q2/close");
    expect(result).toEqual(updated);
  });
});
