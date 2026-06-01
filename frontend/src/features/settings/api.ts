import { api } from "@core/api/client";
import type { TenantConfigResponse } from "./types";

export interface UpdateLLMPayload {
  provider?: string;
  model?: string;
  api_key?: string;
  max_tokens?: number;
  temperature?: number;
}

export interface UpdateEmbeddingPayload {
  provider?: string;
  model?: string;
  api_key?: string;
}

export interface UpdateWhatsAppPayload {
  phone_number_id?: string;
  access_token?: string;
  verify_token?: string;
  app_secret?: string;
}

export interface UpdateTelegramPayload {
  bot_token?: string;
  webhook_secret?: string;
}

export interface UpdateBotPayload {
  name?: string;
  welcome_message?: string;
  language?: string;
}

export async function getSettings(): Promise<TenantConfigResponse> {
  const { data } = await api.get<TenantConfigResponse>("/api/v1/settings");
  return data;
}

export async function updateLLM(payload: UpdateLLMPayload): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/llm", payload);
  return data;
}

export async function updateEmbedding(payload: UpdateEmbeddingPayload): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/embedding", payload);
  return data;
}

export async function updateWhatsApp(payload: UpdateWhatsAppPayload): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/whatsapp", payload);
  return data;
}

export async function updateTelegram(payload: UpdateTelegramPayload): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/telegram", payload);
  return data;
}

export async function updateBot(payload: UpdateBotPayload): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/bot", payload);
  return data;
}
