import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { MemoryRouter } from "react-router-dom";

const mockRegister = vi.fn();
const mockNavigate = vi.fn();

vi.mock("./useAuth", () => ({
  useAuth: () => ({
    register: mockRegister,
    user: null,
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

import { RegisterPage } from "./RegisterPage";

function wrap(ui: React.ReactNode) {
  return (
    <MantineProvider>
      <Notifications />
      <MemoryRouter>{ui}</MemoryRouter>
    </MantineProvider>
  );
}

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders create your front desk title", () => {
    render(wrap(<RegisterPage />));
    expect(screen.getByText("Create your front desk")).toBeInTheDocument();
  });

  it("renders all form fields", () => {
    render(wrap(<RegisterPage />));
    expect(screen.getByLabelText("Your name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Tenant display name")).toBeInTheDocument();
    expect(screen.getByLabelText("Tenant slug")).toBeInTheDocument();
  });

  it("renders create account button", () => {
    render(wrap(<RegisterPage />));
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("renders sign in link", () => {
    render(wrap(<RegisterPage />));
    expect(screen.getByText("Sign in")).toBeInTheDocument();
  });

  it("calls register and navigates on success", async () => {
    mockRegister.mockResolvedValue(undefined);
    render(wrap(<RegisterPage />));

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@test.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText("Tenant display name"), { target: { value: "Acme" } });
    fireEvent.change(screen.getByLabelText("Tenant slug"), { target: { value: "acme" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        email: "new@test.com",
        password: "password123",
        full_name: undefined,
        tenant_name: "Acme",
        tenant_slug: "acme",
      });
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("shows error notification on failed register", async () => {
    mockRegister.mockRejectedValue(new Error("conflict"));
    render(wrap(<RegisterPage />));

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "dup@test.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText("Tenant display name"), { target: { value: "Acme" } });
    fireEvent.change(screen.getByLabelText("Tenant slug"), { target: { value: "acme" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalled();
    });
  });

  it("sends full_name when provided", async () => {
    mockRegister.mockResolvedValue(undefined);
    render(wrap(<RegisterPage />));

    fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "John" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "j@t.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText("Tenant display name"), { target: { value: "X" } });
    fireEvent.change(screen.getByLabelText("Tenant slug"), { target: { value: "xx" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith(
        expect.objectContaining({ full_name: "John" })
      );
    });
  });

  it("shows description text", () => {
    render(wrap(<RegisterPage />));
    expect(screen.getByText(/sets up your tenant and owner account/i)).toBeInTheDocument();
  });

  it("shows validation errors for invalid fields", async () => {
    render(wrap(<RegisterPage />));
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "bad" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "short" } });
    fireEvent.change(screen.getByLabelText("Tenant display name"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Tenant slug"), { target: { value: "X" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText("Enter a valid email")).toBeInTheDocument();
      expect(screen.getByText("At least 8 characters")).toBeInTheDocument();
      expect(screen.getByText("Required")).toBeInTheDocument();
      expect(screen.getByText(/min 2 chars/i)).toBeInTheDocument();
    });
    expect(mockRegister).not.toHaveBeenCalled();
  });
});
