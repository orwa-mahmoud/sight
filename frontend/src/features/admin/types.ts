export interface AdminTenant {
  id: string;
  name: string;
  slug: string;
  status: string;
  owner_email: string | null;
  user_count: number;
  document_count: number;
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_platform_admin: boolean;
  tenant_id: string | null;
  tenant_name: string | null;
  role: string | null;
}
