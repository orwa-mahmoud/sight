import { renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { useBackendData } from "./useBackendData";

interface Row {
  id: string;
}

function wrapper({ children }: { children: React.ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>;
}

/** Build a fake useInfiniteQuery result with the given pages. */
function fakeQuery(
  pages: Array<{ items: Row[]; total?: number }> | undefined,
  over: Partial<{
    hasNextPage: boolean;
    isFetchingNextPage: boolean;
    fetchNextPage: () => Promise<unknown>;
  }> = {},
) {
  return () =>
    ({
      data: pages ? { pages, pageParams: [] } : undefined,
      isLoading: false,
      isFetching: false,
      isFetchingNextPage: over.isFetchingNextPage ?? false,
      hasNextPage: over.hasNextPage ?? false,
      fetchNextPage: over.fetchNextPage ?? vi.fn().mockResolvedValue(undefined),
      error: null,
      refetch: vi.fn(),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    }) as any;
}

function render(opts: Parameters<typeof useBackendData<Row, never, { items: Row[]; total?: number }>>[0]) {
  return renderHook(() => useBackendData<Row, never, { items: Row[]; total?: number }>(opts), { wrapper });
}

describe("useBackendData", () => {
  it("returns empty rows when the query has no data", () => {
    const { result } = render({ usePaginatedQuery: fakeQuery(undefined), paginationMode: "paged" });
    expect(result.current.rows).toEqual([]);
    expect(result.current.total).toBe(0);
  });

  it("paged mode shows only the last page and its total", () => {
    const { result } = render({
      usePaginatedQuery: fakeQuery([{ items: [{ id: "a" }, { id: "b" }], total: 7 }]),
      paginationMode: "paged",
    });
    expect(result.current.rows.map((r) => r.id)).toEqual(["a", "b"]);
    expect(result.current.total).toBe(7);
    expect(result.current.paginationMode).toBe("paged");
  });

  it("paged mode falls back to items.length when total is absent", () => {
    const { result } = render({
      usePaginatedQuery: fakeQuery([{ items: [{ id: "a" }] }]),
      paginationMode: "paged",
    });
    expect(result.current.total).toBe(1);
  });

  it("infinite mode accumulates items across pages and keeps the latest total", () => {
    const { result } = render({
      usePaginatedQuery: fakeQuery([
        { items: [{ id: "a" }], total: 3 },
        { items: [{ id: "b" }, { id: "c" }], total: 3 },
      ]),
      paginationMode: "infinite",
    });
    expect(result.current.rows.map((r) => r.id)).toEqual(["a", "b", "c"]);
    expect(result.current.total).toBe(3);
  });

  it("fetchNextPage triggers the query when another page is available", () => {
    const fetchNextPage = vi.fn().mockResolvedValue(undefined);
    const { result } = render({
      usePaginatedQuery: fakeQuery([{ items: [{ id: "a" }] }], { hasNextPage: true, fetchNextPage }),
      paginationMode: "infinite",
    });
    result.current.fetchNextPage();
    expect(fetchNextPage).toHaveBeenCalledOnce();
  });

  it("fetchNextPage is a no-op when there is no next page", () => {
    const fetchNextPage = vi.fn().mockResolvedValue(undefined);
    const { result } = render({
      usePaginatedQuery: fakeQuery([{ items: [{ id: "a" }] }], { hasNextPage: false, fetchNextPage }),
      paginationMode: "infinite",
    });
    result.current.fetchNextPage();
    expect(fetchNextPage).not.toHaveBeenCalled();
  });

  it("fetchNextPage is a no-op while a page is already loading", () => {
    const fetchNextPage = vi.fn().mockResolvedValue(undefined);
    const { result } = render({
      usePaginatedQuery: fakeQuery([{ items: [{ id: "a" }] }], {
        hasNextPage: true,
        isFetchingNextPage: true,
        fetchNextPage,
      }),
      paginationMode: "infinite",
    });
    result.current.fetchNextPage();
    expect(fetchNextPage).not.toHaveBeenCalled();
  });

  it("uses a custom selectPage projection", () => {
    const { result } = render({
      usePaginatedQuery: (() =>
        ({
          data: { pages: [{ rows: [{ id: "x" }], count: 9 }], pageParams: [] },
          isLoading: false,
          isFetching: false,
          isFetchingNextPage: false,
          hasNextPage: false,
          fetchNextPage: vi.fn(),
          error: null,
          refetch: vi.fn(),
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        }) as any) as never,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      selectPage: (p: any) => ({ items: p.rows, total: p.count }),
      paginationMode: "paged",
    });
    expect(result.current.rows.map((r) => r.id)).toEqual(["x"]);
    expect(result.current.total).toBe(9);
  });
});
