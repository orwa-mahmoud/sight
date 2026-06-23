import type { TableSource } from "@adapttable/mantine";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TextFilter } from "./TextFilter";
import { TestWrapper } from "@test/wrapper";

interface Row {
  id: string;
}

function mockSource(extra: Record<string, unknown>) {
  const setExtra = vi.fn();
  return { source: { extra, setExtra } as unknown as TableSource<Row>, setExtra };
}

describe("TextFilter", () => {
  it("shows the current string filter value", () => {
    const { source } = mockSource({ q: "hello" });
    render(<TextFilter source={source} filterKey="q" label="Search" />, { wrapper: TestWrapper });
    expect(screen.getByLabelText("Search")).toHaveValue("hello");
  });

  it("coerces a non-string filter value to text", () => {
    const { source } = mockSource({ q: 42 });
    render(<TextFilter source={source} filterKey="q" label="Search" />, { wrapper: TestWrapper });
    expect(screen.getByLabelText("Search")).toHaveValue("42");
  });

  it("sets the filter as the user types", () => {
    const { source, setExtra } = mockSource({});
    render(<TextFilter source={source} filterKey="q" label="Search" />, { wrapper: TestWrapper });
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "world" } });
    expect(setExtra).toHaveBeenCalledWith("q", "world");
  });

  it("clears the filter to undefined when emptied", () => {
    const { source, setExtra } = mockSource({ q: "hello" });
    render(<TextFilter source={source} filterKey="q" label="Search" />, { wrapper: TestWrapper });
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "" } });
    expect(setExtra).toHaveBeenCalledWith("q", undefined);
  });
});
