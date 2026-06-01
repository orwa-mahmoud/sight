import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DataTable, SelectFilter, useFrontendData, type ColumnDef } from "@shared/components/datatable";
import { TestWrapper } from "@test/wrapper";

interface Row {
  id: string;
  name: string;
  status: string;
}

const DATA: Row[] = Array.from({ length: 25 }, (_, i) => ({
  id: String(i + 1),
  name: `Item ${i + 1}`,
  status: i % 2 === 0 ? "active" : "inactive",
}));

const COLUMNS: ColumnDef<Row>[] = [
  { key: "name", header: "Name", accessor: (r) => r.name, sortable: true, sortValue: (r) => r.name },
  { key: "status", header: "Status", accessor: (r) => r.status, sortable: true, sortValue: (r) => r.status },
];

function Harness({ onAction }: Readonly<{ onAction?: (row: Row) => void }>) {
  const source = useFrontendData<Row>({ data: DATA, columns: COLUMNS });
  return (
    <DataTable
      source={source}
      columns={COLUMNS}
      rowKey={(r) => r.id}
      tableLabel="Items"
      rowActions={onAction ? [{ key: "view", label: "View", onClick: onAction }] : undefined}
      filters={
        <SelectFilter
          source={source}
          filterKey="status"
          label="Status"
          data={[
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
          ]}
        />
      }
      filterLabels={{ status: (v) => `Status: ${String(v)}` }}
    />
  );
}

function renderTable(props: Readonly<{ onAction?: (row: Row) => void }> = {}) {
  return render(
    <TestWrapper>
      <Harness {...props} />
    </TestWrapper>,
  );
}

describe("DataTable (frontend source)", () => {
  it("renders the first page (default page size)", () => {
    renderTable();
    expect(screen.getByText("Item 1")).toBeInTheDocument();
    expect(screen.getByText("Item 20")).toBeInTheDocument();
    expect(screen.queryByText("Item 21")).not.toBeInTheDocument();
  });

  it("shows the range and paginates to page 2", async () => {
    renderTable();
    expect(screen.getByText("1–20 of 25")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "2" }));
    await waitFor(() => expect(screen.getByText("Item 21")).toBeInTheDocument());
    expect(screen.queryByText("Item 1")).not.toBeInTheDocument();
  });

  it("filters rows via search (debounced)", async () => {
    renderTable();
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "Item 25" } });
    await waitFor(() => expect(screen.getByText("Item 25")).toBeInTheDocument());
    expect(screen.queryByText("Item 1")).not.toBeInTheDocument();
  });

  it("cycles sort asc → desc → none on a sortable header", () => {
    renderTable();
    const button = () => screen.getByRole("button", { name: /Name/ });
    const header = () => screen.getByRole("columnheader", { name: /Name/ });
    fireEvent.click(button());
    expect(header()).toHaveAttribute("aria-sort", "ascending");
    fireEvent.click(button());
    expect(header()).toHaveAttribute("aria-sort", "descending");
    fireEvent.click(button());
    expect(header()).not.toHaveAttribute("aria-sort");
  });

  it("runs a row action", () => {
    const onAction = vi.fn();
    renderTable({ onAction });
    fireEvent.click(screen.getAllByRole("button", { name: "View" })[0]!);
    expect(onAction).toHaveBeenCalledOnce();
    expect(onAction).toHaveBeenCalledWith(DATA[0]);
  });

  it("opens the filters drawer", async () => {
    renderTable();
    fireEvent.click(screen.getByRole("button", { name: "Filters" }));
    await waitFor(() => expect(screen.getByText("Apply filters")).toBeInTheDocument());
  });
});
