import { api } from "@core/api/client";
import type { Question, QuestionStatus } from "./types";

export async function listQuestions(status?: QuestionStatus): Promise<Question[]> {
  const { data } = await api.get<Question[]>("/api/v1/questions", {
    params: status ? { status } : undefined,
  });
  return data;
}

export async function replyToQuestion(id: string, reply: string): Promise<Question> {
  const { data } = await api.post<Question>(`/api/v1/questions/${id}/reply`, { reply });
  return data;
}

export async function closeQuestion(id: string): Promise<Question> {
  const { data } = await api.post<Question>(`/api/v1/questions/${id}/close`);
  return data;
}
