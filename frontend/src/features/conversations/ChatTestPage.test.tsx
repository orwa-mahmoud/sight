import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
});
