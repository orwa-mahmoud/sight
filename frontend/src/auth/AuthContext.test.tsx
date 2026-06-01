import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("@core/api/client", () => ({
  setUnauthorizedHandler: vi.fn(),
}));

vi.mock("./api", () => ({
  login: vi.fn(),
  register: vi.fn(),
  me: vi.fn(),
  logout: vi.fn(),
}));

import { AuthProvider } from "./AuthContext";
import { useAuth } from "./useAuth";
import * as authApi from "./api";

const ME_RESPONSE = {
  id: "u1",
  email: "test@example.com",
  full_name: "Test User",
  is_active: true,
  tenant: { id: "t1", slug: "acme", name: "Acme", role: "owner" },
};

function TestConsumer() {
  const auth = useAuth();
  if (auth.loading) return <div>loading</div>;
  if (auth.user) return <div>user:{auth.user.email}</div>;
  return <div>no-user</div>;
}

function LoginConsumer() {
  const { login, user, loading } = useAuth();
  if (loading) return <div>loading</div>;
  return (
    <div>
      <span>{user ? `user:${user.email}` : "no-user"}</span>
      <button onClick={() => void login("a@b.com", "password")}>login</button>
    </div>
  );
}

function RegisterConsumer() {
  const { register, user, loading } = useAuth();
  if (loading) return <div>loading</div>;
  return (
    <div>
      <span>{user ? `user:${user.email}` : "no-user"}</span>
      <button
        onClick={() =>
          void register({ email: "a@b.com", password: "pw", tenant_name: "T", tenant_slug: "t" })
        }
      >
        register
      </button>
    </div>
  );
}

function LogoutConsumer() {
  const { logout, user, loading } = useAuth();
  if (loading) return <div>loading</div>;
  return (
    <div>
      <span>{user ? `user:${user.email}` : "no-user"}</span>
      <button onClick={logout}>logout</button>
    </div>
  );
}

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>{ui}</AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sets user to null when there is no valid session", async () => {
    vi.mocked(authApi.me).mockRejectedValue(new Error("unauthorized"));
    render(wrap(<TestConsumer />));
    await waitFor(() => expect(screen.getByText("no-user")).toBeInTheDocument());
  });

  it("loads the current user when the session cookie is valid", async () => {
    vi.mocked(authApi.me).mockResolvedValue(ME_RESPONSE);
    render(wrap(<TestConsumer />));
    await waitFor(() => expect(screen.getByText("user:test@example.com")).toBeInTheDocument());
  });

  it("login authenticates then loads the user", async () => {
    vi.mocked(authApi.me).mockRejectedValueOnce(new Error("unauthorized"));
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "new-jwt", token_type: "bearer", user_id: "u1", tenant_id: "t1",
    });
    vi.mocked(authApi.me).mockResolvedValue(ME_RESPONSE);

    render(wrap(<LoginConsumer />));
    await waitFor(() => expect(screen.getByText("no-user")).toBeInTheDocument());

    await act(async () => {
      screen.getByText("login").click();
    });

    await waitFor(() => expect(screen.getByText("user:test@example.com")).toBeInTheDocument());
    expect(authApi.login).toHaveBeenCalledWith("a@b.com", "password");
  });

  it("register authenticates then loads the user", async () => {
    vi.mocked(authApi.me).mockRejectedValueOnce(new Error("unauthorized"));
    vi.mocked(authApi.register).mockResolvedValue({
      access_token: "reg-jwt", token_type: "bearer", user_id: "u2", tenant_id: "t2",
    });
    vi.mocked(authApi.me).mockResolvedValue(ME_RESPONSE);

    render(wrap(<RegisterConsumer />));
    await waitFor(() => expect(screen.getByText("no-user")).toBeInTheDocument());

    await act(async () => {
      screen.getByText("register").click();
    });

    await waitFor(() => expect(screen.getByText("user:test@example.com")).toBeInTheDocument());
    expect(authApi.register).toHaveBeenCalled();
  });

  it("logout clears the user and calls the logout endpoint", async () => {
    vi.mocked(authApi.me).mockResolvedValue(ME_RESPONSE);
    vi.mocked(authApi.logout).mockResolvedValue();

    render(wrap(<LogoutConsumer />));
    await waitFor(() => expect(screen.getByText("user:test@example.com")).toBeInTheDocument());

    await act(async () => {
      screen.getByText("logout").click();
    });

    expect(authApi.logout).toHaveBeenCalled();
    await waitFor(() => expect(screen.getByText("no-user")).toBeInTheDocument());
  });
});
