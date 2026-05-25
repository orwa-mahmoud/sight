import { describe, it, expect } from "vitest";
import type { Question, QuestionStatus } from "./types";

describe("Question type", () => {
  it("has the expected shape", () => {
    const q: Question = {
      id: "1",
      conversation_id: null,
      channel: "whatsapp",
      contact_id: "c-uuid-1234",
      question_text: "Are you open?",
      ai_answer_attempt: null,
      status: "submitted" as QuestionStatus,
      owner_reply: null,
      replied_by_user_id: null,
      replied_at: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    expect(q.status).toBe("submitted");
    expect(q.contact_id).toBe("c-uuid-1234");
  });
});
