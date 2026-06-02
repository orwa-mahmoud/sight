import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@core/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    defaults: { headers: {} },
  },
  setUnauthorizedHandler: vi.fn(),
}));

const mockRefresh = vi.fn().mockResolvedValue(undefined);
const mockNavigate = vi.fn();
let mockUser: { email: string } | null = null;

vi.mock("@auth/useAuth", () => ({
  useAuth: () => ({ user: mockUser, refresh: mockRefresh }),
}));

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => mockNavigate };
});

import { api } from "@core/api/client";
import { InvitePage } from "./InvitePage";

function renderAt(token = "tok-123") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Wrapper = ({ children }: Readonly<{ children: ReactNode }>) => (
    <MantineProvider>
      <ModalsProvider>
        <Notifications />
        <QueryClientProvider client={qc}>
          <MemoryRouter initialEntries={[`/invite/${token}`]}>
            <Routes>
              <Route path="/invite/:token" element={children} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </ModalsProvider>
    </MantineProvider>
  );
  return render(<InvitePage />, { wrapper: Wrapper });
}

const VALID_PREVIEW = {
  tenant_name: "Acme",
  email: "invitee@test.com",
  role: "staff",
  status: "pending",
  valid: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockUser = null;
});

describe("InvitePage", () => {
  it("shows an error for an invalid invite", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { ...VALID_PREVIEW, valid: false } });
    renderAt();
    expect(await screen.findByText(/invalid, expired/i)).toBeInTheDocument();
  });

  it("lets a logged-in matching user accept", async () => {
    mockUser = { email: "invitee@test.com" };
    vi.mocked(api.get).mockResolvedValue({ data: VALID_PREVIEW });
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    renderAt();

    fireEvent.click(await screen.findByRole("button", { name: "Accept" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/api/v1/invitations/token/tok-123/accept"));
    await waitFor(() => expect(mockRefresh).toHaveBeenCalled());
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });

  it("warns when signed in as a different account", async () => {
    mockUser = { email: "someone-else@test.com" };
    vi.mocked(api.get).mockResolvedValue({ data: VALID_PREVIEW });
    renderAt();
    expect(await screen.findByText(/signed in as/i)).toBeInTheDocument();
  });

  it("registers a brand-new user through the invite", async () => {
    mockUser = null;
    vi.mocked(api.get).mockResolvedValue({ data: VALID_PREVIEW });
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    const { container } = renderAt();

    const joinButton = await screen.findByRole("button", { name: "Create account & join" });
    const pwd = container.querySelector('input[type="password"]');
    expect(pwd).not.toBeNull();
    fireEvent.change(pwd!, { target: { value: "supersecure123" } });
    fireEvent.click(joinButton);

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/v1/invitations/token/tok-123/register", {
        password: "supersecure123",
        full_name: undefined,
      }),
    );
  });
});
