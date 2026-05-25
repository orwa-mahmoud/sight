import { api } from "../../core/api/client";
import type { TenantConfigResponse } from "./types";

export async function getSettings(): Promise<TenantConfigResponse> {
  const { data } = await api.get<TenantConfigResponse>("/api/v1/settings");
  return data;
}

export async function updateLLM(payload: Record<string, unknown>): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/llm", payload);
  return data;
}

export async function updateEmbedding(payload: Record<string, unknown>): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/embedding", payload);
  return data;
}

export async function updateWhatsApp(payload: Record<string, unknown>): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/whatsapp", payload);
  return data;
}

export async function updateTelegram(payload: Record<string, unknown>): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/telegram", payload);
  return data;
}

export async function updateBot(payload: Record<string, unknown>): Promise<TenantConfigResponse> {
  const { data } = await api.put<TenantConfigResponse>("/api/v1/settings/bot", payload);
  return data;
}
