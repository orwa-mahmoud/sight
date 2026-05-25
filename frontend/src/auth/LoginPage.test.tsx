import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TestWrapper } from "../test/wrapper";

vi.mock("./useAuth", () => ({
  useAuth: () => ({ login: vi.fn(), user: null, loading: false, register: vi.fn(), logout: vi.fn() }),
}));

describe("LoginPage", () => {
  it("renders login form with email input", async () => {
    const { LoginPage } = await import("./LoginPage");
    render(<LoginPage />, { wrapper: TestWrapper });
    expect(screen.getByPlaceholderText(/owner@example.com/i)).toBeInTheDocument();
  });
});
