export type QuestionStatus = "submitted" | "resolved" | "closed";

export interface Question {
  id: string;
  conversation_id: string | null;
  channel: string;
  asker_name: string | null;
  asker_contact: string | null;
  question_text: string;
  ai_answer_attempt: string | null;
  status: QuestionStatus;
  owner_reply: string | null;
  replied_by_user_id: string | null;
  replied_at: string | null;
  created_at: string;
  updated_at: string;
}
