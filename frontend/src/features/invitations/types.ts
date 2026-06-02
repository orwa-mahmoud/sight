export interface Invitation {
  id: string;
  email: string;
  role: string;
  status: string;
  token: string;
  invite_url: string;
  expires_at: string;
  created_at: string;
}

export interface InvitationPreview {
  tenant_name: string;
  email: string;
  role: string;
  status: string;
  valid: boolean;
}
