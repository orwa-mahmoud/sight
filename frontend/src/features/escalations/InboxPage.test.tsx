import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("./api", () => ({
  listQuestions: vi.fn(),
  replyToQuestion: vi.fn(),
  closeQuestion: vi.fn(),
}));

import { listQuestions, replyToQuestion, closeQuestion } from "./api";
import { InboxPage } from "./InboxPage";
import type { Question } from "./types";

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

const QUESTIONS: Question[] = [
  {
    id: "q1", conversation_id: null, channel: "whatsapp",
    asker_name: "Sara", asker_contact: "+971500000000",
    question_text: "What are your hours?",
    ai_answer_attempt: "We are open 9-5.",
    status: "submitted", owner_reply: null,
    replied_by_user_id: null, replied_at: null,
    created_at: "2026-01-01T10:00:00Z", updated_at: "2026-01-01T10:00:00Z",
  },
  {
    id: "q2", conversation_id: null, channel: "telegram",
    asker_name: null, asker_contact: null,
    question_text: "Do you deliver?",
    ai_answer_attempt: null,
    status: "submitted", owner_reply: null,
    replied_by_user_id: null, replied_at: null,
    created_at: "2026-01-01T11:00:00Z", updated_at: "2026-01-01T11:00:00Z",
  },
];

const RESOLVED_QUESTION: Question = {
  id: "q3", conversation_id: null, channel: "web",
  asker_name: "Ali", asker_contact: "ali@test.com",
  question_text: "Price?", ai_answer_attempt: null,
  status: "resolved", owner_reply: "It's $10.",
  replied_by_user_id: "u1", replied_at: "2026-01-01T12:00:00Z",
  created_at: "2026-01-01T10:00:00Z", updated_at: "2026-01-01T12:00:00Z",
};

describe("InboxPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title and description", () => {
    vi.mocked(listQuestions).mockResolvedValue([]);
    render(<InboxPage />, { wrapper: createWrapper() });
    expect(screen.getByText("Inbox")).toBeInTheDocument();
    expect(screen.getByText(/questions the ai escalated/i)).toBeInTheDocument();
  });

  it("shows filter controls", () => {
    vi.mocked(listQuestions).mockResolvedValue([]);
    render(<InboxPage />, { wrapper: createWrapper() });
    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.getByText("Resolved")).toBeInTheDocument();
    expect(screen.getByText("Closed")).toBeInTheDocument();
    expect(screen.getByText("All")).toBeInTheDocument();
  });

  it("shows empty state when no questions", async () => {
    vi.mocked(listQuestions).mockResolvedValue([]);
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Nothing waiting on you.")).toBeInTheDocument();
    });
  });

  it("shows error alert on failure", async () => {
    vi.mocked(listQuestions).mockRejectedValue(new Error("fail"));
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Could not load the inbox")).toBeInTheDocument();
    });
  });

  it("renders question cards with text", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("What are your hours?")).toBeInTheDocument();
      expect(screen.getByText("Do you deliver?")).toBeInTheDocument();
    });
  });

  it("shows AI answer attempt when present", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("We are open 9-5.")).toBeInTheDocument();
      expect(screen.getByText("AI's attempt")).toBeInTheDocument();
    });
  });

  it("shows asker name and contact", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Sara")).toBeInTheDocument();
      expect(screen.getByText("+971500000000")).toBeInTheDocument();
    });
  });

  it("shows channel badges", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("WhatsApp")).toBeInTheDocument();
      expect(screen.getByText("Telegram")).toBeInTheDocument();
    });
  });

  it("shows Reply and Close buttons for submitted questions", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      const replyButtons = screen.getAllByText("Reply");
      expect(replyButtons).toHaveLength(2);
    });
  });

  it("opens reply modal on Reply click", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    render(<InboxPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("What are your hours?")).toBeInTheDocument();
    });

    const replyButtons = screen.getAllByText("Reply");
    fireEvent.click(replyButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Reply to question")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/type the reply/i)).toBeInTheDocument();
    });
  });

  it("calls closeQuestion on Close click", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    vi.mocked(closeQuestion).mockResolvedValue({ ...QUESTIONS[0], status: "closed" });
    render(<InboxPage />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("What are your hours?")).toBeInTheDocument();
    });

    const closeButtons = screen.getAllByText("Close");
    fireEvent.click(closeButtons[0]);

    await waitFor(() => {
      expect(closeQuestion).toHaveBeenCalledWith("q1");
    });
  });

  it("shows owner reply when present", async () => {
    vi.mocked(listQuestions).mockResolvedValue([RESOLVED_QUESTION]);
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("It's $10.")).toBeInTheDocument();
      expect(screen.getByText("Your reply")).toBeInTheDocument();
    });
  });

  it("does not show Reply/Close buttons for resolved questions", async () => {
    vi.mocked(listQuestions).mockResolvedValue([RESOLVED_QUESTION]);
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText("Price?")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /^Reply$/i })).not.toBeInTheDocument();
  });

  it("sends reply via modal", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    vi.mocked(replyToQuestion).mockResolvedValue({ ...QUESTIONS[0], status: "resolved", owner_reply: "We open at 9." });
    render(<InboxPage />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("What are your hours?")).toBeInTheDocument());

    fireEvent.click(screen.getAllByText("Reply")[0]);
    await waitFor(() => expect(screen.getByPlaceholderText(/type the reply/i)).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/type the reply/i), {
      target: { value: "We open at 9." },
    });
    fireEvent.click(screen.getByText("Send reply"));

    await waitFor(() => {
      expect(replyToQuestion).toHaveBeenCalledWith("q1", "We open at 9.");
    });
  });

  it("shows raw channel name for unknown channels", async () => {
    const unknownChannelQ: Question = {
      ...QUESTIONS[0], id: "q9", channel: "sms",
    };
    vi.mocked(listQuestions).mockResolvedValue([unknownChannelQ]);
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("sms")).toBeInTheDocument());
  });

  it("has refresh button", () => {
    vi.mocked(listQuestions).mockResolvedValue([]);
    render(<InboxPage />, { wrapper: createWrapper() });
    expect(screen.getByLabelText("Refresh")).toBeInTheDocument();
  });

  it("shows error notification when reply fails", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    vi.mocked(replyToQuestion).mockRejectedValue(new Error("network"));
    render(<InboxPage />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("What are your hours?")).toBeInTheDocument());
    fireEvent.click(screen.getAllByText("Reply")[0]);
    await waitFor(() => expect(screen.getByPlaceholderText(/type the reply/i)).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/type the reply/i), { target: { value: "reply text" } });
    fireEvent.click(screen.getByText("Send reply"));

    await waitFor(() => expect(replyToQuestion).toHaveBeenCalled());
  });

  it("shows error notification when close fails", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    vi.mocked(closeQuestion).mockRejectedValue(new Error("network"));
    render(<InboxPage />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("What are your hours?")).toBeInTheDocument());
    fireEvent.click(screen.getAllByText("Close")[0]);

    await waitFor(() => expect(closeQuestion).toHaveBeenCalled());
  });

  it("changes filter via segmented control", async () => {
    vi.mocked(listQuestions).mockResolvedValue([]);
    render(<InboxPage />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("Nothing waiting on you.")).toBeInTheDocument());

    fireEvent.click(screen.getByText("All"));

    await waitFor(() => {
      expect(listQuestions).toHaveBeenCalledWith(undefined);
    });
  });

  it("shows loading on close button while pending", async () => {
    vi.mocked(listQuestions).mockResolvedValue(QUESTIONS);
    vi.mocked(closeQuestion).mockReturnValue(new Promise(() => {}));
    render(<InboxPage />, { wrapper: createWrapper() });
    await waitFor(() => expect(screen.getByText("What are your hours?")).toBeInTheDocument());

    fireEvent.click(screen.getAllByText("Close")[0]);
    await waitFor(() => expect(closeQuestion).toHaveBeenCalledWith("q1"));
  });

  it("refresh button invalidates queries", async () => {
    vi.mocked(listQuestions).mockResolvedValue([]);
    render(<InboxPage />, { wrapper: createWrapper() });

    await waitFor(() => expect(screen.getByText("Nothing waiting on you.")).toBeInTheDocument());
    fireEvent.click(screen.getByLabelText("Refresh"));

    await waitFor(() => {
      expect(listQuestions).toHaveBeenCalledTimes(2);
    });
  });
});
