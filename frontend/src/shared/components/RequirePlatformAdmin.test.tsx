import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "@auth/context";
import { RequirePlatformAdmin } from "./RequirePlatformAdmin";

function renderGuard(user: AuthContextValue["user"], loading = false) {
  const value: AuthContextValue = {
    user,
    loading,
    login: vi.fn(),
    register: vi.fn(),
    refresh: vi.fn(),
    logout: vi.fn(),
  };
  return render(
    <MantineProvider>
      <AuthContext.Provider value={value}>
        <MemoryRouter initialEntries={["/admin/tenants"]}>
          <Routes>
            <Route path="/" element={<div>home</div>} />
            <Route
              path="/admin/tenants"
              element={
                <RequirePlatformAdmin>
                  <div>admin area</div>
                </RequirePlatformAdmin>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </MantineProvider>,
  );
}

const baseUser = {
  id: "u1",
  email: "a@b.com",
  full_name: null,
  is_active: true,
  tenant: { id: "t1", slug: "t", name: "T", role: "owner" },
};

describe("RequirePlatformAdmin", () => {
  it("renders children for a platform admin", () => {
    renderGuard({ ...baseUser, is_platform_admin: true });
    expect(screen.getByText("admin area")).toBeInTheDocument();
  });

  it("redirects a non-admin to home", () => {
    renderGuard({ ...baseUser, is_platform_admin: false });
    expect(screen.getByText("home")).toBeInTheDocument();
    expect(screen.queryByText("admin area")).not.toBeInTheDocument();
  });

  it("shows a loader while auth is resolving", () => {
    const { container } = renderGuard(null, true);
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });
});
