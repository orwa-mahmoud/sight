import { api } from "@core/api/client";
import type { Invitation, InvitationPreview } from "./types";

export async function createInvitation(email: string): Promise<Invitation> {
  const { data } = await api.post<Invitation>("/api/v1/invitations", { email });
  return data;
}

export async function listInvitations(): Promise<Invitation[]> {
  const { data } = await api.get<Invitation[]>("/api/v1/invitations");
  return data;
}

export async function revokeInvitation(invitationId: string): Promise<void> {
  await api.post(`/api/v1/invitations/${invitationId}/revoke`);
}

export async function previewInvitation(token: string): Promise<InvitationPreview> {
  const { data } = await api.get<InvitationPreview>(`/api/v1/invitations/token/${token}`);
  return data;
}

export async function acceptInvitation(token: string): Promise<void> {
  await api.post(`/api/v1/invitations/token/${token}/accept`);
}

export async function rejectInvitation(token: string): Promise<void> {
  await api.post(`/api/v1/invitations/token/${token}/reject`);
}

export async function registerViaInvitation(
  token: string,
  password: string,
  fullName?: string,
): Promise<void> {
  await api.post(`/api/v1/invitations/token/${token}/register`, {
    password,
    full_name: fullName,
  });
}
