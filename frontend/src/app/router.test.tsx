import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("@auth/useAuth", () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

import { AppRoutes } from "./router";

function wrap(initialEntries: string[]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MantineProvider>
        <Notifications />
        <QueryClientProvider client={qc}>
          <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
        </QueryClientProvider>
      </MantineProvider>
    );
  };
}

describe("AppRoutes", () => {
  it("renders login page at /login", () => {
    render(<AppRoutes />, { wrapper: wrap(["/login"]) });
    expect(screen.getByText(/sign in to/i)).toBeInTheDocument();
  });

  it("renders register page at /register", () => {
    render(<AppRoutes />, { wrapper: wrap(["/register"]) });
    expect(screen.getByText(/create your front desk/i)).toBeInTheDocument();
  });

  it("redirects unauthenticated user from / to login", () => {
    render(<AppRoutes />, { wrapper: wrap(["/"]) });
    expect(screen.queryByText("Inbox")).not.toBeInTheDocument();
  });
});
