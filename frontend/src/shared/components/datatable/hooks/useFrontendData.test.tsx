import { act, renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { ColumnDef } from "../types";
import { useFrontendData, type UseFrontendDataOptions } from "./useFrontendData";

interface Row {
  name: string;
  age: number | null;
  status: string;
}

const columns: ColumnDef<Row>[] = [
  { key: "name", header: "Name", sortable: true, sortValue: (r) => r.name },
  { key: "age", header: "Age", sortable: true, sortValue: (r) => r.age },
  { key: "status", header: "Status" },
];

const data: Row[] = [
  { name: "Charlie", age: 30, status: "ready" },
  { name: "alice", age: 20, status: "failed" },
  { name: "Bob", age: null, status: "ready" },
];

function wrapper({ children }: { children: React.ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>;
}

function setup(opts: Partial<UseFrontendDataOptions<Row>> = {}) {
  return renderHook(() => useFrontendData<Row>({ data, columns, ...opts }), { wrapper });
}

describe("useFrontendData", () => {
  it("returns all rows by default", () => {
    const { result } = setup({ paginationMode: "paged" });
    expect(result.current.total).toBe(3);
    expect(result.current.rows).toHaveLength(3);
  });

  it("filters by case-insensitive search", () => {
    const { result } = setup({ paginationMode: "paged" });
    act(() => result.current.setSearch("ALICE"));
    expect(result.current.rows.map((r) => r.name)).toEqual(["alice"]);
  });

  it("sorts a string column ascending then descending (locale-aware)", () => {
    const { result } = setup({ paginationMode: "paged" });
    act(() => result.current.setSort("name", "asc"));
    expect(result.current.rows.map((r) => r.name)).toEqual(["alice", "Bob", "Charlie"]);
    act(() => result.current.setSort("name", "desc"));
    expect(result.current.rows.map((r) => r.name)).toEqual(["Charlie", "Bob", "alice"]);
  });

  it("sorts a numeric column and orders null values last", () => {
    const { result } = setup({ paginationMode: "paged" });
    act(() => result.current.setSort("age", "asc"));
    expect(result.current.rows.map((r) => r.age)).toEqual([20, 30, null]);
  });

  it("filters via an exact extra match", () => {
    const { result } = setup({ paginationMode: "paged" });
    act(() => result.current.setExtra("status", "ready"));
    expect(result.current.rows.map((r) => r.name).sort()).toEqual(["Bob", "Charlie"]);
  });

  it("clears an extra filter when set to undefined", () => {
    const { result } = setup({ paginationMode: "paged" });
    act(() => result.current.setExtra("status", "failed"));
    expect(result.current.rows).toHaveLength(1);
    act(() => result.current.setExtra("status", undefined));
    expect(result.current.rows).toHaveLength(3);
  });

  it("paginates in paged mode and clamps an out-of-range page", () => {
    const { result } = setup({ paginationMode: "paged" });
    act(() => result.current.setLimit(2));
    expect(result.current.rows).toHaveLength(2);
    act(() => result.current.setPage(2));
    expect(result.current.rows).toHaveLength(1);
    act(() => result.current.setPage(99));
    expect(result.current.page).toBe(2); // clamped to last page
  });

  it("accumulates pages in infinite mode via fetchNextPage", () => {
    const { result } = setup({ paginationMode: "infinite" });
    act(() => result.current.setLimit(2));
    expect(result.current.rows).toHaveLength(2);
    expect(result.current.hasNextPage).toBe(true);
    act(() => result.current.fetchNextPage());
    expect(result.current.rows).toHaveLength(3);
    expect(result.current.hasNextPage).toBe(false);
  });

  it("resets the infinite slice when the filter changes", () => {
    const { result } = setup({ paginationMode: "infinite" });
    act(() => result.current.setLimit(2));
    act(() => result.current.fetchNextPage());
    expect(result.current.rows).toHaveLength(3);
    act(() => result.current.setSearch("a")); // matches alice + Charlie
    expect(result.current.rows.length).toBeLessThanOrEqual(2);
  });

  it("treats two null sort values as equal (stable order)", () => {
    const d: Row[] = [
      { name: "a", age: null, status: "x" },
      { name: "b", age: null, status: "y" },
    ];
    const { result } = setup({ data: d, paginationMode: "paged" });
    act(() => result.current.setSort("age", "asc"));
    expect(result.current.rows.map((r) => r.name)).toEqual(["a", "b"]);
  });

  it("sorts a column without a sortValue using the raw field", () => {
    const { result } = setup({ paginationMode: "paged" });
    act(() => result.current.setSort("status", "asc")); // status column has no sortValue
    expect(result.current.rows.map((r) => r.status)).toEqual(["failed", "ready", "ready"]);
  });

  it("ignores an empty-string extra filter", () => {
    const { result } = setup({ paginationMode: "paged" });
    act(() => result.current.setExtra("status", ""));
    expect(result.current.rows).toHaveLength(3);
  });

  it("searches object fields by their JSON representation", () => {
    interface MetaRow {
      name: string;
      meta: { role: string };
    }
    const d: MetaRow[] = [
      { name: "a", meta: { role: "admin" } },
      { name: "b", meta: { role: "user" } },
    ];
    const cols: ColumnDef<MetaRow>[] = [
      { key: "name", header: "Name" },
      { key: "meta", header: "Meta" },
    ];
    const { result } = renderHook(
      () => useFrontendData<MetaRow>({ data: d, columns: cols, searchKeys: ["meta"], paginationMode: "paged" }),
      { wrapper },
    );
    act(() => result.current.setSearch("admin"));
    expect(result.current.rows.map((r) => r.name)).toEqual(["a"]);
  });

  it("clearAll removes search, sort, and filters", () => {
    const { result } = setup({ paginationMode: "paged" });
    act(() => result.current.setSearch("alice"));
    act(() => result.current.setExtra("status", "failed"));
    act(() => result.current.clearAll());
    expect(result.current.rows).toHaveLength(3);
    expect(result.current.search).toBe("");
  });
});
