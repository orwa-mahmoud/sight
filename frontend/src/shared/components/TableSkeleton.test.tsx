import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TableSkeleton } from "./TableSkeleton";
import { TestWrapper } from "@test/wrapper";

describe("TableSkeleton", () => {
  it("renders the requested number of skeleton rows", () => {
    const { container } = render(<TableSkeleton rows={4} />, { wrapper: TestWrapper });
    expect(container.querySelectorAll(".mantine-Skeleton-root")).toHaveLength(4);
  });

  it("defaults to 6 rows", () => {
    const { container } = render(<TableSkeleton />, { wrapper: TestWrapper });
    expect(container.querySelectorAll(".mantine-Skeleton-root")).toHaveLength(6);
  });
});
