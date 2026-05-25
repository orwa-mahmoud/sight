import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("../../core/api/client", () => ({
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

import { api } from "../../core/api/client";
import { DocumentsPage } from "./DocumentsPage";

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

const DOC_LIST = [
  {
    id: "d1", filename: "guide.pdf", mime_type: "application/pdf",
    size_bytes: 2048, status: "ready", chunk_count: 12, error: null,
    created_at: "2026-01-01T10:00:00Z", updated_at: "2026-01-01T10:00:00Z",
  },
  {
    id: "d2", filename: "notes.md", mime_type: "text/markdown",
    size_bytes: 512, status: "ingesting", chunk_count: 0, error: null,
    created_at: "2026-01-01T11:00:00Z", updated_at: "2026-01-01T11:00:00Z",
  },
];

describe("DocumentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title and description", () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    expect(screen.getByText("Knowledge base")).toBeInTheDocument();
    expect(screen.getByText(/upload pdfs/i)).toBeInTheDocument();
  });

  it("shows empty state when no documents", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("No documents yet.")).toBeInTheDocument();
    });
  });

  it("shows error alert on failure", async () => {
    vi.mocked(api.get).mockRejectedValue(new Error("fail"));
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Could not load documents")).toBeInTheDocument();
    });
  });

  it("shows upload button", () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    expect(screen.getByText("Upload file")).toBeInTheDocument();
  });

  it("shows document table with data", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: DOC_LIST });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("guide.pdf")).toBeInTheDocument();
      expect(screen.getByText("notes.md")).toBeInTheDocument();
    });
  });

  it("shows status badges", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: DOC_LIST });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("ready")).toBeInTheDocument();
      expect(screen.getByText("ingesting")).toBeInTheDocument();
    });
  });

  it("shows chunk count", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: DOC_LIST });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("12")).toBeInTheDocument();
    });
  });

  it("formats file size (KB)", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: DOC_LIST });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("2.0 KB")).toBeInTheDocument();
    });
  });

  it("shows delete button for each doc", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: DOC_LIST });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      const deleteButtons = screen.getAllByText("Delete");
      expect(deleteButtons).toHaveLength(2);
    });
  });

  it("calls delete API when delete confirmed", async () => {
    vi.spyOn(globalThis, "confirm").mockReturnValue(true);
    vi.mocked(api.get).mockResolvedValue({ data: DOC_LIST });
    vi.mocked(api.delete).mockResolvedValue({});
    render(<DocumentsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("guide.pdf")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(api.delete).toHaveBeenCalledWith("/api/v1/documents/d1");
    });
    vi.mocked(globalThis.confirm).mockRestore();
  });

  it("does not delete when confirm is cancelled", async () => {
    vi.spyOn(globalThis, "confirm").mockReturnValue(false);
    vi.mocked(api.get).mockResolvedValue({ data: DOC_LIST });
    render(<DocumentsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("guide.pdf")).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText("Delete");
    fireEvent.click(deleteButtons[0]);

    expect(api.delete).not.toHaveBeenCalled();
    vi.mocked(globalThis.confirm).mockRestore();
  });

  it("formats MB size correctly", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [{
        ...DOC_LIST[0], id: "d3", size_bytes: 2_500_000,
      }],
    });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("2.4 MB")).toBeInTheDocument();
    });
  });

  it("shows fallback gray badge for unknown status", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [{ ...DOC_LIST[0], id: "d5", status: "unknown_status" }],
    });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("unknown_status")).toBeInTheDocument();
    });
  });

  it("formats byte size correctly", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [{
        ...DOC_LIST[0], id: "d4", size_bytes: 500,
      }],
    });
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("500 B")).toBeInTheDocument();
    });
  });

  it("uploads file via FileButton and shows success", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    vi.mocked(api.post).mockResolvedValue({ data: DOC_LIST[0] });
    const { container } = render(<DocumentsPage />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("Upload file")).toBeInTheDocument());

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["hello"], "test.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/api/v1/documents",
        expect.any(FormData),
        expect.objectContaining({ headers: { "Content-Type": "multipart/form-data" }, timeout: 120_000 }),
      );
    });
  });

  it("shows error notification when upload fails", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    vi.mocked(api.post).mockRejectedValue(new Error("upload failed"));
    const { container } = render(<DocumentsPage />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("Upload file")).toBeInTheDocument());

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["bad"], "bad.exe", { type: "application/octet-stream" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalled();
    });
  });

  it("shows loading on the correct delete button while pending", async () => {
    vi.spyOn(globalThis, "confirm").mockReturnValue(true);
    vi.mocked(api.get).mockResolvedValue({ data: DOC_LIST });
    vi.mocked(api.delete).mockReturnValue(new Promise(() => {}));
    render(<DocumentsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getAllByText("Delete")).toHaveLength(2));

    fireEvent.click(screen.getAllByText("Delete")[0]);

    await waitFor(() => {
      expect(api.delete).toHaveBeenCalledWith("/api/v1/documents/d1");
    });
    vi.mocked(globalThis.confirm).mockRestore();
  });
});
