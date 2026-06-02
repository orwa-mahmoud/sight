import { describe, it, expect } from "vitest";
import type { MeResponse, RegisterRequest, TokenResponse } from "./types";

describe("Auth types", () => {
  it("TokenResponse has expected shape", () => {
    const t: TokenResponse = {
      access_token: "jwt.token.here",
      token_type: "bearer",
      user_id: "uuid",
      tenant_id: "uuid",
    };
    expect(t.token_type).toBe("bearer");
  });

  it("MeResponse has expected shape", () => {
    const me: MeResponse = {
      id: "uuid",
      email: "test@test.com",
      full_name: "Test User",
      is_active: true,
      is_platform_admin: false,
      tenant: { id: "uuid", slug: "test", name: "Test", role: "owner" },
    };
    expect(me.tenant.role).toBe("owner");
  });

  it("RegisterRequest has expected shape", () => {
    const r: RegisterRequest = {
      email: "a@b.com",
      password: "password",
      tenant_name: "T",
      tenant_slug: "t",
    };
    expect(r.email).toBe("a@b.com");
  });
});
