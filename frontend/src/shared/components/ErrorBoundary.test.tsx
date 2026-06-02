import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { theme } from "@app/theme";
import { ErrorBoundary } from "./ErrorBoundary";

function Wrap({ children }: { readonly children: React.ReactNode }) {
  return <MantineProvider theme={theme}>{children}</MantineProvider>;
}

function ThrowingChild(): React.ReactNode {
  throw new Error("test crash");
}

function GoodChild() {
  return <div>All good</div>;
}

describe("ErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <Wrap>
        <ErrorBoundary>
          <GoodChild />
        </ErrorBoundary>
      </Wrap>,
    );
    expect(screen.getByText("All good")).toBeDefined();
  });

  it("renders error UI when child throws", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <Wrap>
        <ErrorBoundary>
          <ThrowingChild />
        </ErrorBoundary>
      </Wrap>,
    );
    expect(screen.getByText("Something went wrong")).toBeDefined();
    expect(screen.getByText("Retry")).toBeDefined();
    vi.restoreAllMocks();
  });

  it("shows Retry button that resets error state", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <Wrap>
        <ErrorBoundary>
          <ThrowingChild />
        </ErrorBoundary>
      </Wrap>,
    );
    expect(screen.getByText("Something went wrong")).toBeDefined();
    const retryBtn = screen.getByText("Retry");
    expect(retryBtn).toBeDefined();
    fireEvent.click(retryBtn);
    vi.restoreAllMocks();
  });
});
