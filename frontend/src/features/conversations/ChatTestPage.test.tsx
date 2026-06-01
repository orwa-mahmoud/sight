import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
import { ChatTestPage } from "./ChatTestPage";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <MantineProvider>
      <Notifications />
      <QueryClientProvider client={qc}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

describe("ChatTestPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title and description", () => {
    render(wrap(<ChatTestPage />));
    expect(screen.getByText("Chat (test mode)")).toBeInTheDocument();
    expect(screen.getByText(/talk to your ai front desk/i)).toBeInTheDocument();
  });

  it("shows empty state hint", () => {
    render(wrap(<ChatTestPage />));
    expect(screen.getByText(/send a message to test/i)).toBeInTheDocument();
  });

  it("renders textarea and send button", () => {
    render(wrap(<ChatTestPage />));
    expect(screen.getByPlaceholderText("Type a message...")).toBeInTheDocument();
    expect(screen.getByText("Send")).toBeInTheDocument();
  });

  it("sends a message and shows response", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { response: "Hi from AI", thread_id: "t1", escalated: false, request_id: "r1" },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "Hello" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => {
      expect(screen.getByText("Hello")).toBeInTheDocument();
      expect(screen.getByText("Hi from AI")).toBeInTheDocument();
    });
    expect(api.post).toHaveBeenCalledWith("/api/v1/chat", { message: "Hello" });
  });

  it("sends thread_id in subsequent messages", async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({
        data: { response: "First reply", thread_id: "t42", escalated: false, request_id: "r1" },
      })
      .mockResolvedValueOnce({
        data: { response: "Second reply", thread_id: "t42", escalated: false, request_id: "r2" },
      });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "msg1" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("First reply")).toBeInTheDocument());
    expect(api.post).toHaveBeenCalledWith("/api/v1/chat", { message: "msg1" });

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "msg2" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("Second reply")).toBeInTheDocument());
    expect(api.post).toHaveBeenCalledWith("/api/v1/chat", { message: "msg2", thread_id: "t42" });
  });

  it("shows user and AI labels", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { response: "reply", thread_id: "t1", escalated: false, request_id: "r1" },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "hi" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => {
      expect(screen.getByText("You")).toBeInTheDocument();
      expect(screen.getByText("AI")).toBeInTheDocument();
    });
  });

  it("does not send empty message", () => {
    render(wrap(<ChatTestPage />));
    fireEvent.click(screen.getByText("Send"));
    expect(api.post).not.toHaveBeenCalled();
  });

  it("sends on Enter key without shift", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { response: "r", thread_id: "t1", escalated: false, request_id: "r1" },
    });
    render(wrap(<ChatTestPage />));

    const ta = screen.getByPlaceholderText("Type a message...");
    fireEvent.change(ta, { target: { value: "enter msg" } });
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: false });

    await waitFor(() => expect(api.post).toHaveBeenCalled());
  });

  it("handles API error gracefully", async () => {
    vi.mocked(api.post).mockRejectedValue(new Error("fail"));
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "fail" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("fail")).toBeInTheDocument());
  });

  it("shows escalation notice when escalated", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { response: "escalated reply", thread_id: "t1", escalated: true, request_id: "r1" },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "q" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("escalated reply")).toBeInTheDocument());
  });

  it("does not send on Shift+Enter", () => {
    render(wrap(<ChatTestPage />));
    const ta = screen.getByPlaceholderText("Type a message...");
    fireEvent.change(ta, { target: { value: "newline" } });
    fireEvent.keyDown(ta, { key: "Enter", shiftKey: true });
    expect(api.post).not.toHaveBeenCalled();
  });

  it("does not send on non-Enter key", () => {
    render(wrap(<ChatTestPage />));
    const ta = screen.getByPlaceholderText("Type a message...");
    fireEvent.change(ta, { target: { value: "typing" } });
    fireEvent.keyDown(ta, { key: "a", shiftKey: false });
    expect(api.post).not.toHaveBeenCalled();
  });

  it("renders RAG sources with the document filename", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [{ id: "d1", filename: "guide.pdf" }] });
    vi.mocked(api.post).mockResolvedValue({
      data: {
        response: "From your guide",
        thread_id: "t1",
        escalated: false,
        request_id: "r1",
        sources: [{ document_id: "d1", snippet: "the answer text", score: 0.91 }],
      },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "q" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("From your guide")).toBeInTheDocument());
    expect(screen.getByText("Sources:")).toBeInTheDocument();
    const sourceBadge = screen.getByText("guide.pdf");
    expect(sourceBadge).toBeInTheDocument();

    // Snippet is keyboard/tap accessible: revealed on click (not hover-only).
    fireEvent.click(sourceBadge);
    await waitFor(() => expect(screen.getByText("the answer text")).toBeInTheDocument());
  });

  it("falls back to a short id when the document filename is unknown", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    vi.mocked(api.post).mockResolvedValue({
      data: {
        response: "answer",
        thread_id: "t1",
        escalated: false,
        request_id: "r1",
        sources: [{ document_id: "abcdef1234567890", snippet: "snip", score: 0.5 }],
      },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "q" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("answer")).toBeInTheDocument());
    expect(screen.getByText("abcdef12…")).toBeInTheDocument();
  });

  it("shows an escalated badge on the message", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { response: "esc", thread_id: "t1", escalated: true, request_id: "r1" },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "q" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("Escalated to inbox")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /view in inbox/i })).toHaveAttribute("href", "/inbox");
  });

  it("sends a suggested prompt from the empty state", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { response: "ans", thread_id: "t1", escalated: false, request_id: "r1" },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.click(screen.getByText("What are your opening hours?"));

    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/v1/chat", { message: "What are your opening hours?" }),
    );
  });

  it("previews the configured bot greeting in the empty state", async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url === "/api/v1/settings") {
        return Promise.resolve({ data: { bot_name: "Aria", bot_welcome_message: "Hi! I'm Aria." } });
      }
      return Promise.resolve({ data: [] });
    });
    render(wrap(<ChatTestPage />));
    await waitFor(() => expect(screen.getByText("Hi! I'm Aria.")).toBeInTheDocument());
    expect(screen.getByText("Aria")).toBeInTheDocument();
  });

  it("warns when some documents are still processing", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [{ id: "d1", filename: "a.pdf", status: "ingesting" }],
    });
    render(wrap(<ChatTestPage />));
    await waitFor(() => expect(screen.getByText(/still processing/i)).toBeInTheDocument());
  });

  it("nudges the owner to upload documents when none exist", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    render(wrap(<ChatTestPage />));
    await waitFor(() => expect(screen.getByText("No documents uploaded yet")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Upload documents" })).toHaveAttribute("href", "/documents");
  });

  it("does not nudge to upload when documents exist", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [{ id: "d1", filename: "a.pdf" }] });
    render(wrap(<ChatTestPage />));
    // Give the documents query a tick to resolve, then assert the banner is absent.
    await waitFor(() => expect(screen.getByText("Chat (test mode)")).toBeInTheDocument());
    expect(screen.queryByText("No documents uploaded yet")).not.toBeInTheDocument();
  });

  it("shows the response latency on the AI message", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { response: "timed reply", thread_id: "t1", escalated: false, request_id: "r1" },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "q" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("timed reply")).toBeInTheDocument());
    // A latency label like "0.00s" / "1.2s" is rendered next to the AI label.
    expect(screen.getByText(/^\d+\.\d+s$/)).toBeInTheDocument();
  });

  it("shows token usage when the response includes token counts", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        response: "counted reply",
        thread_id: "t1",
        escalated: false,
        request_id: "r1",
        input_tokens: 120,
        output_tokens: 30,
      },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "q" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText("counted reply")).toBeInTheDocument());
    expect(screen.getByText(/150 tokens/)).toBeInTheDocument();
  });

  it("resets the conversation", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { response: "reply", thread_id: "t1", escalated: false, request_id: "r1" },
    });
    render(wrap(<ChatTestPage />));

    fireEvent.change(screen.getByPlaceholderText("Type a message..."), { target: { value: "hi" } });
    fireEvent.click(screen.getByText("Send"));
    await waitFor(() => expect(screen.getByText("reply")).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText("New conversation"));
    expect(screen.queryByText("reply")).not.toBeInTheDocument();
    expect(screen.getByText(/send a message to test/i)).toBeInTheDocument();
  });
});
