import type { TableSource } from "@adapttable/mantine";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SelectFilter } from "./SelectFilter";
import { TestWrapper } from "@test/wrapper";

interface Row {
  id: string;
}

const DATA = [
  { value: "active", label: "Active" },
  { value: "closed", label: "Closed" },
];

function mockSource(extra: Record<string, unknown>) {
  const setExtra = vi.fn();
  return { source: { extra, setExtra } as unknown as TableSource<Row>, setExtra };
}

describe("SelectFilter", () => {
  it("renders the searchable input showing the current selection", () => {
    const { source } = mockSource({ status: "active" }); // exercises toSelectValue's string branch
    render(<SelectFilter source={source} filterKey="status" label="Status" data={DATA} />, { wrapper: TestWrapper });
    expect(screen.getByDisplayValue("Active")).toBeInTheDocument();
  });

  it("renders with no selection when the filter is unset", () => {
    const { source } = mockSource({}); // exercises toSelectValue's null branch
    render(<SelectFilter source={source} filterKey="status" label="Status" data={DATA} />, { wrapper: TestWrapper });
    expect(screen.getAllByLabelText("Status")[0]).toBeInTheDocument();
  });
});
