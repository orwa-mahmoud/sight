export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  tenant_id: string;
}

export interface TenantSummary {
  id: string;
  slug: string;
  name: string;
  role: string;
}

export interface MeResponse {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_platform_admin: boolean;
  tenant: TenantSummary;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  tenant_name: string;
  tenant_slug: string;
}
