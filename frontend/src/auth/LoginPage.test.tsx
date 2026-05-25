import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { MemoryRouter } from "react-router-dom";

const mockLogin = vi.fn();
const mockNavigate = vi.fn();

vi.mock("./useAuth", () => ({
  useAuth: () => ({
    login: mockLogin,
    user: null,
    loading: false,
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

import { LoginPage } from "./LoginPage";

function wrap(ui: React.ReactNode) {
  return (
    <MantineProvider>
      <Notifications />
      <MemoryRouter>{ui}</MemoryRouter>
    </MantineProvider>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders sign in title", () => {
    render(wrap(<LoginPage />));
    expect(screen.getByText(/sign in to/i)).toBeInTheDocument();
    expect(screen.getByText("frontdesk")).toBeInTheDocument();
  });

  it("renders email and password inputs", () => {
    render(wrap(<LoginPage />));
    expect(screen.getByPlaceholderText("owner@example.com")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders sign in button", () => {
    render(wrap(<LoginPage />));
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("renders link to register page", () => {
    render(wrap(<LoginPage />));
    expect(screen.getByText("Create an account")).toBeInTheDocument();
  });

  it("calls login and navigates on successful submit", async () => {
    mockLogin.mockResolvedValue(undefined);
    render(wrap(<LoginPage />));

    fireEvent.change(screen.getByPlaceholderText("owner@example.com"), {
      target: { value: "test@test.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("test@test.com", "password123");
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("shows error notification on failed login", async () => {
    mockLogin.mockRejectedValue(new Error("bad creds"));
    render(wrap(<LoginPage />));

    fireEvent.change(screen.getByPlaceholderText("owner@example.com"), {
      target: { value: "bad@test.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrongpass1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalled();
    });
  });

  it("shows description text", () => {
    render(wrap(<LoginPage />));
    expect(screen.getByText("Your AI front desk dashboard.")).toBeInTheDocument();
  });

  it("shows validation error for invalid email", async () => {
    render(wrap(<LoginPage />));
    fireEvent.change(screen.getByPlaceholderText("owner@example.com"), { target: { value: "bad" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText("Enter a valid email")).toBeInTheDocument();
      expect(screen.getByText("At least 8 characters")).toBeInTheDocument();
    });
    expect(mockLogin).not.toHaveBeenCalled();
  });
});
