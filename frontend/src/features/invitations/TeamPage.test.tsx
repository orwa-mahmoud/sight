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
import { TeamPage } from "./TeamPage";

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

const INVITES = [
  {
    id: "inv-1",
    email: "pending@test.com",
    role: "staff",
    status: "pending",
    token: "tok-1",
    invite_url: "http://localhost:5173/invite/tok-1",
    expires_at: "2026-12-01T00:00:00Z",
    created_at: "2026-06-01T00:00:00Z",
  },
  {
    id: "inv-2",
    email: "accepted@test.com",
    role: "staff",
    status: "accepted",
    token: "tok-2",
    invite_url: "http://localhost:5173/invite/tok-2",
    expires_at: "2026-12-01T00:00:00Z",
    created_at: "2026-06-01T00:00:00Z",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe("TeamPage", () => {
  it("lists existing invitations", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: INVITES });
    render(<TeamPage />, { wrapper: createWrapper() });
    expect(await screen.findByText("pending@test.com")).toBeInTheDocument();
    expect(screen.getByText("accepted@test.com")).toBeInTheDocument();
  });

  it("creates an invitation from the form", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    vi.mocked(api.post).mockResolvedValue({ data: { ...INVITES[0] } });
    render(<TeamPage />, { wrapper: createWrapper() });

    const input = await screen.findByLabelText("Invite by email");
    fireEvent.change(input, { target: { value: "newhire@test.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/v1/invitations", { email: "newhire@test.com" }),
    );
  });

  it("offers copy + revoke only for pending invites", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: INVITES });
    render(<TeamPage />, { wrapper: createWrapper() });
    await screen.findByText("pending@test.com");
    // One pending invite → exactly one copy + one revoke action.
    expect(screen.getByRole("button", { name: "Copy invite link" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revoke" })).toBeInTheDocument();
  });

  it("revokes a pending invitation after confirmation", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: INVITES });
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    render(<TeamPage />, { wrapper: createWrapper() });
    await screen.findByText("pending@test.com");

    fireEvent.click(screen.getByRole("button", { name: "Revoke" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Revoke" }));

    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/api/v1/invitations/inv-1/revoke"));
  });

  it("copies the invite link to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    vi.mocked(api.get).mockResolvedValue({ data: INVITES });
    render(<TeamPage />, { wrapper: createWrapper() });
    await screen.findByText("pending@test.com");

    fireEvent.click(screen.getByRole("button", { name: "Copy invite link" }));
    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith("http://localhost:5173/invite/tok-1"),
    );
  });
});
