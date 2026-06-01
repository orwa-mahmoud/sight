import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthContext } from "@auth/context";
import { RequireAuth } from "./RequireAuth";

describe("RequireAuth", () => {
  it("shows loader when loading", () => {
    const { container } = render(
      <MantineProvider>
        <MemoryRouter>
          <AuthContext.Provider value={{ user: null, loading: true, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}>
            <RequireAuth><div>Protected</div></RequireAuth>
          </AuthContext.Provider>
        </MemoryRouter>
      </MantineProvider>
    );
    expect(container.querySelector(".mantine-Loader-root")).toBeTruthy();
    expect(screen.queryByText("Protected")).not.toBeInTheDocument();
  });

  it("redirects to /login when not authenticated", () => {
    render(
      <MantineProvider>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <AuthContext.Provider value={{ user: null, loading: false, login: vi.fn(), register: vi.fn(), logout: vi.fn() }}>
            <Routes>
              <Route path="/dashboard" element={<RequireAuth><div>Protected</div></RequireAuth>} />
              <Route path="/login" element={<div>Login Page</div>} />
            </Routes>
          </AuthContext.Provider>
        </MemoryRouter>
      </MantineProvider>
    );
    expect(screen.queryByText("Protected")).not.toBeInTheDocument();
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <AuthContext.Provider value={{
            user: { id: "u1", email: "a@b.com", full_name: "T", is_active: true, tenant: { id: "t1", slug: "t", name: "T", role: "owner" } },
            loading: false, login: vi.fn(), register: vi.fn(), logout: vi.fn(),
          }}>
            <RequireAuth><div>Protected</div></RequireAuth>
          </AuthContext.Provider>
        </MemoryRouter>
      </MantineProvider>
    );
    expect(screen.getByText("Protected")).toBeInTheDocument();
  });
});
