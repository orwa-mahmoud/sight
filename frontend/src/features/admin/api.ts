import { api } from "@core/api/client";
import type { AdminTenant, AdminUser } from "./types";

export async function listTenants(): Promise<AdminTenant[]> {
  const { data } = await api.get<AdminTenant[]>("/api/v1/admin/tenants");
  return data;
}

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await api.get<AdminUser[]>("/api/v1/admin/users");
  return data;
}

export async function setTenantActive(tenantId: string, active: boolean): Promise<void> {
  const action = active ? "activate" : "deactivate";
  await api.post(`/api/v1/admin/tenants/${tenantId}/${action}`);
}

export async function setUserActive(userId: string, active: boolean): Promise<void> {
  const action = active ? "activate" : "deactivate";
  await api.post(`/api/v1/admin/users/${userId}/${action}`);
}
