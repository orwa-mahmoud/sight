import { api } from "@core/api/client";
import type { MeResponse, RegisterRequest, TokenResponse } from "./types";

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/api/v1/auth/login", { email, password });
  return data;
}

export async function register(req: RegisterRequest): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/api/v1/auth/register", req);
  return data;
}

export async function me(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>("/api/v1/auth/me");
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/api/v1/auth/logout");
}
