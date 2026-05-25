import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TestWrapper } from "../test/wrapper";

vi.mock("./useAuth", () => ({
  useAuth: () => ({ register: vi.fn(), user: null, loading: false, login: vi.fn(), logout: vi.fn() }),
}));

describe("RegisterPage", () => {
  it("renders create account form", async () => {
    const { RegisterPage } = await import("./RegisterPage");
    render(<RegisterPage />, { wrapper: TestWrapper });
    expect(screen.getByText(/create your front desk/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });
});
