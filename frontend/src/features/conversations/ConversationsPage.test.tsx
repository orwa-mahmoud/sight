import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
import { ConversationsPage } from "./ConversationsPage";

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

describe("ConversationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title", () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    render(<ConversationsPage />, { wrapper: createWrapper() });
    expect(screen.getByText("Conversations")).toBeInTheDocument();
  });

  it("shows empty state when no conversations", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    render(<ConversationsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("No conversations yet.")).toBeInTheDocument();
    });
  });

  it("shows error alert on failure", async () => {
    vi.mocked(api.get).mockRejectedValue(new Error("fail"));
    render(<ConversationsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Could not load data")).toBeInTheDocument();
    });
  });

  it("shows conversations table with data", async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url.includes("daily-summary")) {
        return {
          data: { date: "2026-01-01", total_messages: 42, active_conversations: 5, questions_escalated: 3 },
        };
      }
      return {
        data: [
          {
            id: "c1",
            thread_id: "thread-abc-123",
            channel: "whatsapp",
            last_message_at: "2026-01-01T10:00:00Z",
            created_at: "2026-01-01T09:00:00Z",
          },
          {
            id: "c2",
            thread_id: "thread-def-456",
            channel: "telegram",
            last_message_at: null,
            created_at: "2026-01-01T08:00:00Z",
          },
        ],
      };
    });
    render(<ConversationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("thread-abc-123")).toBeInTheDocument();
      expect(screen.getByText("thread-def-456")).toBeInTheDocument();
    });
  });

  it("shows stat cards when daily summary loads", async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url.includes("daily-summary")) {
        return {
          data: { date: "2026-01-01", total_messages: 100, active_conversations: 7, questions_escalated: 2 },
        };
      }
      return { data: [] };
    });
    render(<ConversationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("100")).toBeInTheDocument();
      expect(screen.getByText("7")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
    });
  });

  it("shows channel badge labels", async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url.includes("daily-summary"))
        return {
          data: { date: "2026-01-01", total_messages: 0, active_conversations: 0, questions_escalated: 0 },
        };
      return {
        data: [
          {
            id: "c1",
            thread_id: "t1",
            channel: "whatsapp",
            last_message_at: "2026-01-01T10:00:00Z",
            created_at: "2026-01-01T09:00:00Z",
          },
        ],
      };
    });
    render(<ConversationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("WhatsApp")).toBeInTheDocument();
    });
  });

  it("truncates long thread IDs", async () => {
    const longId = "a".repeat(50);
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url.includes("daily-summary"))
        return {
          data: { date: "2026-01-01", total_messages: 0, active_conversations: 0, questions_escalated: 0 },
        };
      return {
        data: [
          {
            id: "c1",
            thread_id: longId,
            channel: "web",
            last_message_at: null,
            created_at: "2026-01-01T09:00:00Z",
          },
        ],
      };
    });
    render(<ConversationsPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(`${longId.slice(0, 40)}...`)).toBeInTheDocument();
    });
  });

  it("opens a transcript drawer and shows the conversation messages", async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url.includes("daily-summary")) {
        return {
          data: { date: "2026-01-01", total_messages: 0, active_conversations: 0, questions_escalated: 0 },
        };
      }
      if (url.includes("/messages")) {
        return {
          data: [
            { id: "m1", role: "user", content: "Do you deliver?", created_at: "2026-01-01T10:00:00Z" },
            {
              id: "m2",
              role: "assistant",
              content: "Yes, we deliver daily.",
              created_at: "2026-01-01T10:00:05Z",
            },
          ],
        };
      }
      return {
        data: [
          {
            id: "c1",
            thread_id: "thread-abc",
            channel: "whatsapp",
            last_message_at: "2026-01-01T10:00:00Z",
            created_at: "2026-01-01T09:00:00Z",
          },
        ],
      };
    });
    render(<ConversationsPage />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("thread-abc")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "View transcript" }));

    await waitFor(() => expect(screen.getByText("Yes, we deliver daily.")).toBeInTheDocument());
    expect(screen.getByText("Do you deliver?")).toBeInTheDocument();
    expect(screen.getByText("Visitor")).toBeInTheDocument();
  });

  it("shows an empty-transcript message when a conversation has no messages", async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url.includes("daily-summary")) {
        return {
          data: { date: "2026-01-01", total_messages: 0, active_conversations: 0, questions_escalated: 0 },
        };
      }
      if (url.includes("/messages")) return { data: [] };
      return {
        data: [
          {
            id: "c1",
            thread_id: "thread-x",
            channel: "web",
            last_message_at: null,
            created_at: "2026-01-01T09:00:00Z",
          },
        ],
      };
    });
    render(<ConversationsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("thread-x")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "View transcript" }));
    await waitFor(() =>
      expect(screen.getByText("No messages in this conversation yet.")).toBeInTheDocument(),
    );
  });

  it("shows a transcript error when messages fail to load", async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url.includes("daily-summary")) {
        return {
          data: { date: "2026-01-01", total_messages: 0, active_conversations: 0, questions_escalated: 0 },
        };
      }
      if (url.includes("/messages")) throw new Error("boom");
      return {
        data: [
          {
            id: "c1",
            thread_id: "thread-y",
            channel: "web",
            last_message_at: null,
            created_at: "2026-01-01T09:00:00Z",
          },
        ],
      };
    });
    render(<ConversationsPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("thread-y")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "View transcript" }));
    await waitFor(() => expect(screen.getByText("Could not load the transcript.")).toBeInTheDocument());
  });

  it("shows raw channel name when not in lookup map", async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url.includes("daily-summary"))
        return {
          data: { date: "2026-01-01", total_messages: 0, active_conversations: 0, questions_escalated: 0 },
        };
      return {
        data: [
          {
            id: "c1",
            thread_id: "t1",
            channel: "sms",
            last_message_at: null,
            created_at: "2026-01-01T09:00:00Z",
          },
        ],
      };
    });
    render(<ConversationsPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("sms")).toBeInTheDocument();
    });
  });
});
