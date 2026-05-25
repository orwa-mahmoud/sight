import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TestWrapper } from "../../test/wrapper";
import { ChatTestPage } from "./ChatTestPage";

vi.mock("../../core/api/client", () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn(), interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } }, defaults: { headers: {} } },
  getToken: () => "tok", setToken: vi.fn(), clearToken: vi.fn(),
}));

describe("ChatTestPage", () => {
  it("renders chat interface", () => {
    render(<ChatTestPage />, { wrapper: TestWrapper });
    expect(screen.getByPlaceholderText(/type a message/i)).toBeInTheDocument();
  });
});
