import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@core/api/client", () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

import { api } from "@core/api/client";
import { login, register, me } from "./api";

describe("auth API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("login posts to /api/v1/auth/login", async () => {
    const token = { access_token: "jwt", token_type: "bearer", user_id: "u1", tenant_id: "t1" };
    vi.mocked(api.post).mockResolvedValue({ data: token });

    const result = await login("user@test.com", "pass1234");

    expect(api.post).toHaveBeenCalledWith("/api/v1/auth/login", {
      email: "user@test.com",
      password: "pass1234",
    });
    expect(result).toEqual(token);
  });

  it("register posts to /api/v1/auth/register", async () => {
    const token = { access_token: "jwt2", token_type: "bearer", user_id: "u2", tenant_id: "t2" };
    vi.mocked(api.post).mockResolvedValue({ data: token });

    const req = { email: "new@t.com", password: "pw123456", tenant_name: "Acme", tenant_slug: "acme" };
    const result = await register(req);

    expect(api.post).toHaveBeenCalledWith("/api/v1/auth/register", req);
    expect(result).toEqual(token);
  });

  it("me gets /api/v1/auth/me", async () => {
    const user = {
      id: "u1", email: "a@b.com", full_name: "T", is_active: true,
      tenant: { id: "t1", slug: "t", name: "T", role: "owner" },
    };
    vi.mocked(api.get).mockResolvedValue({ data: user });

    const result = await me();

    expect(api.get).toHaveBeenCalledWith("/api/v1/auth/me");
    expect(result).toEqual(user);
  });
});
