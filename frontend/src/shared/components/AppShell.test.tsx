import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MantineProvider } from "@mantine/core";
import { AuthContext, type AuthContextValue } from "@auth/context";
import { ProtectedShell } from "./AppShell";

// The shell mounts the global IngestionProgress (which polls via useQuery). These
// tests cover shell structure, not ingestion, so stub it to keep them isolated
// from the query client — IngestionProgress has its own dedicated test.
vi.mock("./IngestionProgress", () => ({ IngestionProgress: () => null }));

const USER_WITH_NAME = {
  id: "u1",
  email: "owner@acme.com",
  full_name: "Acme Owner",
  is_active: true,
  is_platform_admin: false,
  tenant: { id: "t1", slug: "acme", name: "Acme Corp", role: "owner" },
};

const USER_NO_NAME = {
  id: "u2",
  email: "noname@acme.com",
  full_name: null,
  is_active: true,
  is_platform_admin: false,
  tenant: { id: "t1", slug: "acme", name: "Acme Corp", role: "owner" },
};

const base: Omit<AuthContextValue, "user"> = {
  loading: false,
  login: vi.fn(),
  register: vi.fn(),
  refresh: vi.fn(),
  logout: vi.fn(),
};

function renderShell(user: typeof USER_WITH_NAME | typeof USER_NO_NAME, path = "/") {
  return render(
    <MantineProvider>
      <MemoryRouter initialEntries={[path]}>
        <AuthContext.Provider value={{ ...base, user }}>
          <ProtectedShell>
            <div>Page</div>
          </ProtectedShell>
        </AuthContext.Provider>
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("ProtectedShell", () => {
  it("renders the brand name", () => {
    renderShell(USER_WITH_NAME);
    expect(screen.getByText("frontdesk")).toBeInTheDocument();
  });

  it("renders all nav links", () => {
    renderShell(USER_WITH_NAME);
    expect(screen.getByText("Inbox")).toBeInTheDocument();
    expect(screen.getByText("Chat (test)")).toBeInTheDocument();
    expect(screen.getByText("Conversations")).toBeInTheDocument();
    expect(screen.getByText("Documents")).toBeInTheDocument();
    expect(screen.getByText("Usage & cost")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("shows owner-only nav (Team, Settings) for owners", () => {
    renderShell(USER_WITH_NAME);
    expect(screen.getByText("Team")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("hides owner-only nav (Team, Settings) for staff members", () => {
    renderShell({ ...USER_WITH_NAME, tenant: { ...USER_WITH_NAME.tenant, role: "staff" } });
    expect(screen.queryByText("Team")).not.toBeInTheDocument();
    expect(screen.queryByText("Settings")).not.toBeInTheDocument();
  });

  it("hides the admin nav section for non-admins", () => {
    renderShell(USER_WITH_NAME);
    expect(screen.queryByText("Platform")).not.toBeInTheDocument();
    expect(screen.queryByText("Tenants")).not.toBeInTheDocument();
  });

  it("shows the admin nav section for platform admins", () => {
    renderShell({ ...USER_WITH_NAME, is_platform_admin: true });
    expect(screen.getByText("Platform")).toBeInTheDocument();
    expect(screen.getByText("Tenants")).toBeInTheDocument();
    expect(screen.getByText("Users")).toBeInTheDocument();
  });

  it("renders user display name when present", () => {
    renderShell(USER_WITH_NAME);
    expect(screen.getByText("Acme Owner")).toBeInTheDocument();
  });

  it("falls back to email when full_name is null", () => {
    renderShell(USER_NO_NAME);
    expect(screen.getByText("noname@acme.com")).toBeInTheDocument();
  });

  it("renders avatar with first letter of name", () => {
    renderShell(USER_WITH_NAME);
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("renders avatar with first letter of email when no name", () => {
    renderShell(USER_NO_NAME);
    expect(screen.getByText("N")).toBeInTheDocument();
  });

  it("renders tenant info in sidebar", () => {
    renderShell(USER_WITH_NAME);
    expect(screen.getByText("acme")).toBeInTheDocument();
    expect(screen.getByText("owner")).toBeInTheDocument();
  });

  it("renders sign out button", () => {
    renderShell(USER_WITH_NAME);
    expect(screen.getByLabelText("Sign out")).toBeInTheDocument();
  });

  it("renders children", () => {
    renderShell(USER_WITH_NAME);
    expect(screen.getByText("Page")).toBeInTheDocument();
  });

  it("exposes a focusable main landmark the skip link can target", () => {
    const { container } = renderShell(USER_WITH_NAME);
    const main = container.querySelector("#main-content");
    expect(main).not.toBeNull();
    // tabIndex=-1 lets the skip link move keyboard focus, not just scroll.
    expect(main).toHaveAttribute("tabindex", "-1");
  });

  it("marks non-root nav as active on matching path", () => {
    renderShell(USER_WITH_NAME, "/documents");
    const docsLink = screen.getByText("Documents").closest("a");
    expect(docsLink).toHaveAttribute("data-active", "true");
  });

  it("handles user with no name, no email, no tenant details", () => {
    const minimalUser = {
      id: "u3",
      email: undefined,
      full_name: undefined,
      is_active: true,
      tenant: { id: "t1", slug: undefined, name: "X", role: undefined },
    } as unknown as typeof USER_WITH_NAME;
    renderShell(minimalUser);
    expect(screen.getByText("?")).toBeInTheDocument();
  });

  it("reveals the skip-to-content link on focus and hides it on blur", () => {
    renderShell(USER_WITH_NAME);
    const link = screen.getByText("Skip to content");
    expect(link).toHaveStyle({ position: "absolute" });
    fireEvent.focus(link);
    expect(link).toHaveStyle({ position: "fixed" });
    fireEvent.blur(link);
    expect(link).toHaveStyle({ position: "absolute" });
  });

  it("calls logout when sign out is clicked", () => {
    const logout = vi.fn();
    render(
      <MantineProvider>
        <MemoryRouter>
          <AuthContext.Provider value={{ ...base, user: USER_WITH_NAME, logout }}>
            <ProtectedShell>
              <div>Page</div>
            </ProtectedShell>
          </AuthContext.Provider>
        </MemoryRouter>
      </MantineProvider>,
    );
    fireEvent.click(screen.getByLabelText("Sign out"));
    expect(logout).toHaveBeenCalled();
  });
});
