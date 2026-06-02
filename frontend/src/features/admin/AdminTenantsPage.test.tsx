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

import { api } from "@core/api/client";
import { AdminTenantsPage } from "./AdminTenantsPage";

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

const TENANTS = [
  {
    id: "ten-active",
    name: "Acme Corp",
    slug: "acme",
    status: "active",
    owner_email: "owner@acme.com",
    user_count: 3,
    document_count: 12,
  },
  {
    id: "ten-suspended",
    name: "Globex",
    slug: "globex",
    status: "suspended",
    owner_email: "ceo@globex.com",
    user_count: 1,
    document_count: 0,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AdminTenantsPage", () => {
  it("lists tenants with owner + status", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: TENANTS });
    render(<AdminTenantsPage />, { wrapper: createWrapper() });
    expect(await screen.findByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("Globex")).toBeInTheDocument();
    expect(screen.getByText("owner@acme.com")).toBeInTheDocument();
  });

  it("offers Suspend for active tenants and Activate for suspended ones", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: TENANTS });
    render(<AdminTenantsPage />, { wrapper: createWrapper() });
    await screen.findByText("Acme Corp");
    expect(screen.getByRole("button", { name: "Suspend tenant" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Activate tenant" })).toBeInTheDocument();
  });

  it("suspends a tenant after confirmation", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: TENANTS });
    vi.mocked(api.post).mockResolvedValue({ data: { id: "ten-active", status: "suspended" } });
    render(<AdminTenantsPage />, { wrapper: createWrapper() });
    await screen.findByText("Acme Corp");

    fireEvent.click(screen.getByRole("button", { name: "Suspend tenant" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Suspend tenant" }));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/v1/admin/tenants/ten-active/deactivate"),
    );
  });

  it("activates a suspended tenant (no confirmation needed)", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: TENANTS });
    vi.mocked(api.post).mockResolvedValue({ data: { id: "ten-suspended", status: "active" } });
    render(<AdminTenantsPage />, { wrapper: createWrapper() });
    await screen.findByText("Globex");

    fireEvent.click(screen.getByRole("button", { name: "Activate tenant" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/v1/admin/tenants/ten-suspended/activate"),
    );
  });
});
