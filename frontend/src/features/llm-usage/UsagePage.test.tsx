import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("@core/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    defaults: { headers: {} },
  },
  getToken: () => "tok",
  setToken: vi.fn(),
  clearToken: vi.fn(),
}));

import { api } from "@core/api/client";
import { UsagePage } from "./UsagePage";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MantineProvider>
        <Notifications />
        <QueryClientProvider client={qc}>
          <MemoryRouter>{children}</MemoryRouter>
        </QueryClientProvider>
      </MantineProvider>
    );
  };
}

const STATS = {
  total_input_tokens: 150_000,
  total_output_tokens: 30_000,
  total_cache_read_tokens: 50_000,
  total_input_cost: "1.50",
  total_cache_read_cost: "0.25",
  total_output_cost: "3.00",
  total_cost: "4.75",
  total_calls: 420,
};

describe("UsagePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title", () => {
    vi.mocked(api.get).mockResolvedValue({ data: STATS });
    render(<UsagePage />, { wrapper: createWrapper() });
    expect(screen.getByText(/usage & cost/i)).toBeInTheDocument();
  });

  it("shows error alert on failure", async () => {
    vi.mocked(api.get).mockRejectedValue(new Error("fail"));
    render(<UsagePage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Could not load usage stats.")).toBeInTheDocument();
    });
  });

  it("shows stat cards with formatted values", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: STATS });
    render(<UsagePage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("$4.75")).toBeInTheDocument();
      expect(screen.getByText("420")).toBeInTheDocument();
      expect(screen.getByText("150.0K")).toBeInTheDocument();
      expect(screen.getByText("30.0K")).toBeInTheDocument();
    });
  });

  it("shows cost breakdown", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: STATS });
    render(<UsagePage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Cost breakdown")).toBeInTheDocument();
      expect(screen.getByText("$1.50")).toBeInTheDocument();
      expect(screen.getByText("$0.25")).toBeInTheDocument();
      expect(screen.getByText("$3.00")).toBeInTheDocument();
    });
  });

  it("shows cache hit tokens when non-zero", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: STATS });
    render(<UsagePage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Cache hit tokens")).toBeInTheDocument();
      expect(screen.getByText("50.0K")).toBeInTheDocument();
    });
  });

  it("hides cache hit row when zero", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { ...STATS, total_cache_read_tokens: 0 },
    });
    render(<UsagePage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("$4.75")).toBeInTheDocument();
    });
    expect(screen.queryByText("Cache hit tokens")).not.toBeInTheDocument();
  });

  it("formats tiny costs with 6 decimals", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { ...STATS, total_cost: "0.001234" },
    });
    render(<UsagePage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("$0.001234")).toBeInTheDocument();
    });
  });

  it("formats million-scale tokens", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { ...STATS, total_input_tokens: 2_500_000 },
    });
    render(<UsagePage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("2.5M")).toBeInTheDocument();
    });
  });

  it("formats NaN cost as $0.00", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { ...STATS, total_cost: "not-a-number" },
    });
    render(<UsagePage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("$0.00")).toBeInTheDocument();
    });
  });

  it("formats small token counts as plain numbers", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { ...STATS, total_output_tokens: 42 },
    });
    render(<UsagePage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument();
    });
  });
});
