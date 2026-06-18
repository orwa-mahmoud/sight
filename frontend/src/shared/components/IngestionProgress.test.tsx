import { render, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
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
import { AuthContext, type AuthContextValue } from "@auth/context";
import { IngestionProgress } from "./IngestionProgress";

const USER = {
  id: "u1",
  email: "owner@acme.com",
  full_name: "Acme Owner",
  is_active: true,
  is_platform_admin: false,
  tenant: { id: "t1", slug: "acme", name: "Acme Corp", role: "owner" },
};

const baseAuth: Omit<AuthContextValue, "user"> = {
  loading: false,
  login: vi.fn(),
  register: vi.fn(),
  refresh: vi.fn(),
  logout: vi.fn(),
};

function doc(id: string, filename: string, status = "ingesting") {
  return { id, filename, status };
}

function renderProgress(user: AuthContextValue["user"] = USER) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: Readonly<{ children: ReactNode }>) {
    return (
      <MantineProvider>
        <QueryClientProvider client={qc}>
          <AuthContext.Provider value={{ ...baseAuth, user }}>
            <MemoryRouter>{children}</MemoryRouter>
          </AuthContext.Provider>
        </QueryClientProvider>
      </MantineProvider>
    );
  }
  return render(<IngestionProgress />, { wrapper: Wrapper });
}

describe("IngestionProgress", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing when no documents are processing", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    renderProgress();
    await waitFor(() => expect(api.get).toHaveBeenCalledWith("/api/v1/documents/processing"));
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows in-flight documents read from the backend", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [doc("d1", "policy.pdf"), doc("d2", "faq.md", "uploaded")] });
    renderProgress();
    expect(await screen.findByText("policy.pdf")).toBeInTheDocument();
    expect(screen.getByText("faq.md")).toBeInTheDocument();
    // i18n count interpolation reflects how many are still ingesting.
    expect(screen.getByText("Processing 2 document(s)…")).toBeInTheDocument();
  });

  it("collapses the overflow into a +N more line", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [doc("d1", "a.pdf"), doc("d2", "b.pdf"), doc("d3", "c.pdf"), doc("d4", "d.pdf"), doc("d5", "e.pdf")],
    });
    renderProgress();
    expect(await screen.findByText("a.pdf")).toBeInTheDocument();
    expect(screen.getByText("c.pdf")).toBeInTheDocument();
    // Only the first three filenames render; the rest collapse.
    expect(screen.queryByText("d.pdf")).toBeNull();
    expect(screen.getByText("+2 more")).toBeInTheDocument();
  });

  it("does not query the backend when signed out", () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    renderProgress(null);
    expect(api.get).not.toHaveBeenCalled();
  });
});
