import { MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@auth/useAuth", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "owner@acme.com",
      full_name: "Owner",
      is_active: true,
      tenant: { id: "t1", slug: "acme", name: "Acme", role: "owner" },
    },
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("@core/api/client", () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    post: vi.fn().mockResolvedValue({ data: [] }),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    defaults: { headers: {} },
  },
  setUnauthorizedHandler: vi.fn(),
}));

import { AppRoutes } from "./router";

function wrap(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MantineProvider>
        <ModalsProvider>
          <Notifications />
          <QueryClientProvider client={qc}>
            <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
          </QueryClientProvider>
        </ModalsProvider>
      </MantineProvider>
    );
  };
}

describe("AppRoutes lazy loading", () => {
  it.each([
    ["/", "Questions the AI escalated to you."],
    ["/conversations", "All threads between askers and the AI."],
    ["/documents", /upload pdfs/i],
    ["/usage", /per-tenant token/i],
    ["/chat", "Chat (test mode)"],
    ["/settings", /configure your llm provider/i],
  ])("lazy-loads the protected route %s", async (path, marker) => {
    render(<AppRoutes />, { wrapper: wrap(path) });
    await waitFor(() => expect(screen.getByText(marker)).toBeInTheDocument());
  });
});
