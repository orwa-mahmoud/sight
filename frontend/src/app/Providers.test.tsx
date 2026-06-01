import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@auth/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { Providers } from "./Providers";

describe("Providers", () => {
  it("renders children within all provider layers", () => {
    render(
      <Providers>
        <div>App Content</div>
      </Providers>,
    );
    expect(screen.getByText("App Content")).toBeInTheDocument();
  });
});
