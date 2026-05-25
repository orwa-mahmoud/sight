import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TestWrapper } from "../../test/wrapper";
import { ConversationsPage } from "./ConversationsPage";

vi.mock("../../core/api/client", () => ({
  api: { get: vi.fn().mockResolvedValue({ data: [] }), post: vi.fn(), put: vi.fn(), delete: vi.fn(), interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } }, defaults: { headers: {} } },
  getToken: () => "tok", setToken: vi.fn(), clearToken: vi.fn(),
}));

describe("ConversationsPage", () => {
  it("renders title", () => {
    render(<ConversationsPage />, { wrapper: TestWrapper });
    expect(screen.getByText("Conversations")).toBeInTheDocument();
  });
});
