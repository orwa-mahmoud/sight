import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
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

vi.mock("@auth/useAuth", () => ({
  useAuth: () => ({ user: { id: "me-admin", is_platform_admin: true }, loading: false }),
}));

import { api } from "@core/api/client";
import { AdminUsersPage } from "./AdminUsersPage";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: Readonly<{ children: ReactNode }>) {
    return (
      <MantineProvider>
        <ModalsProvider>
          <Notifications />
          <QueryClientProvider client={qc}>
            <MemoryRouter>{children}</MemoryRouter>
          </QueryClientProvider>
        </ModalsProvider>
      </MantineProvider>
    );
  };
}

const USERS = [
  {
    id: "u-normal",
    email: "normal@acme.com",
    full_name: "Normal User",
    is_active: true,
    is_platform_admin: false,
    tenant_id: "t1",
    tenant_name: "Acme",
    role: "owner",
  },
  {
    id: "u-inactive",
    email: "inactive@acme.com",
    full_name: null,
    is_active: false,
    is_platform_admin: false,
    tenant_id: "t2",
    tenant_name: "Beta",
    role: "staff",
  },
  {
    id: "me-admin",
    email: "admin@acme.com",
    full_name: "Me Admin",
    is_active: true,
    is_platform_admin: true,
    tenant_id: "t3",
    tenant_name: "Admin Co",
    role: "owner",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AdminUsersPage", () => {
  it("lists users with email + tenant", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: USERS });
    render(<AdminUsersPage />, { wrapper: createWrapper() });
    expect(await screen.findByText("normal@acme.com")).toBeInTheDocument();
    expect(screen.getByText("admin@acme.com")).toBeInTheDocument();
  });

  it("offers Disable for active users and Enable for an inactive one", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: USERS });
    render(<AdminUsersPage />, { wrapper: createWrapper() });
    await screen.findByText("normal@acme.com");
    expect(screen.getAllByRole("button", { name: "Disable user" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Enable user" })).toBeInTheDocument();
  });

  it("disables a user after confirmation", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: USERS });
    vi.mocked(api.post).mockResolvedValue({ data: { id: "u-normal", is_active: false } });
    render(<AdminUsersPage />, { wrapper: createWrapper() });
    await screen.findByText("normal@acme.com");

    // Click the only enabled Disable button (the normal user's; self + admin are disabled).
    const enabled = screen
      .getAllByRole("button", { name: "Disable user" })
      .find((b) => !b.hasAttribute("disabled"));
    fireEvent.click(enabled!);
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Disable user" }));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/v1/admin/users/u-normal/deactivate"),
    );
  });

  it("disables the Disable action for the current admin's own row and other admins", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: USERS });
    render(<AdminUsersPage />, { wrapper: createWrapper() });
    await screen.findByText("admin@acme.com");
    // The only enabled "Disable user" button is for the normal user — self + admin
    // rows render a disabled button.
    const disableButtons = screen.getAllByRole("button", { name: "Disable user" });
    const enabled = disableButtons.filter((b) => !b.hasAttribute("disabled"));
    expect(enabled).toHaveLength(1);
  });
});
