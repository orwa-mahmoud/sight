import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { useTableUrlState } from "./useTableUrlState";

function wrapper(initialEntries: string[] = ["/"]) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>;
  };
}

describe("useTableUrlState", () => {
  it("defaults to page 1, default limit, empty search/sort/extra", () => {
    const { result } = renderHook(() => useTableUrlState(), { wrapper: wrapper() });
    expect(result.current.page).toBe(1);
    expect(result.current.limit).toBe(20);
    expect(result.current.search).toBe("");
    expect(result.current.sortBy).toBeUndefined();
    expect(result.current.sortDir).toBeUndefined();
    expect(result.current.extra).toEqual({});
  });

  it("parses state from the initial URL", () => {
    const { result } = renderHook(
      () => useTableUrlState({ numberExtraKeys: ["count"], arrayExtraKeys: ["tags"] }),
      {
        wrapper: wrapper([
          "/?q=hi&page=3&page_size=50&sort=name&sort_dir=desc&filter_status=ready&filter_count=5&filter_tags=a,b",
        ]),
      },
    );
    expect(result.current.search).toBe("hi");
    expect(result.current.page).toBe(3);
    expect(result.current.limit).toBe(50);
    expect(result.current.sortBy).toBe("name");
    expect(result.current.sortDir).toBe("desc");
    expect(result.current.extra).toEqual({ status: "ready", count: 5, tags: ["a", "b"] });
  });

  it("setPage/setLimit/setSearch update and reset page", () => {
    const { result } = renderHook(() => useTableUrlState(), { wrapper: wrapper() });
    act(() => result.current.setPage(4));
    expect(result.current.page).toBe(4);
    act(() => result.current.setLimit(50));
    expect(result.current.limit).toBe(50);
    expect(result.current.page).toBe(1); // limit change resets page
    act(() => result.current.setPage(2));
    act(() => result.current.setSearch("hello"));
    expect(result.current.search).toBe("hello");
    expect(result.current.page).toBe(1); // search resets page
    act(() => result.current.setSearch(""));
    expect(result.current.search).toBe("");
  });

  it("cycles sort asc -> desc -> cleared", () => {
    const { result } = renderHook(() => useTableUrlState(), { wrapper: wrapper() });
    act(() => result.current.setSort("name", "asc"));
    expect(result.current.sortBy).toBe("name");
    expect(result.current.sortDir).toBe("asc");
    act(() => result.current.setSort("name", "desc"));
    expect(result.current.sortDir).toBe("desc");
    act(() => result.current.setSort(undefined));
    expect(result.current.sortBy).toBeUndefined();
    expect(result.current.sortDir).toBeUndefined();
  });

  it("setExtra sets, serializes arrays, and clears", () => {
    const { result } = renderHook(() => useTableUrlState({ arrayExtraKeys: ["tags"] }), {
      wrapper: wrapper(),
    });
    act(() => result.current.setExtra("status", "ready"));
    expect(result.current.extra.status).toBe("ready");
    act(() => result.current.setExtra("tags", ["x", "y"]));
    expect(result.current.extra.tags).toEqual(["x", "y"]);
    act(() => result.current.setExtra("status", undefined));
    expect(result.current.extra.status).toBeUndefined();
  });

  it("clearAll removes search, sort, page and filters", () => {
    const { result } = renderHook(() => useTableUrlState(), {
      wrapper: wrapper(["/?q=hi&page=2&sort=name&filter_status=ready&keep=this"]),
    });
    act(() => result.current.clearAll());
    expect(result.current.search).toBe("");
    expect(result.current.sortBy).toBeUndefined();
    expect(result.current.page).toBe(1);
    expect(result.current.extra).toEqual({});
  });

  it("honors defaults for limit and sort", () => {
    const { result } = renderHook(
      () => useTableUrlState({ defaults: { limit: 10, sortBy: "created_at", sortDir: "desc" } }),
      { wrapper: wrapper() },
    );
    expect(result.current.limit).toBe(10);
    expect(result.current.sortBy).toBe("created_at");
    expect(result.current.sortDir).toBe("desc");
  });
});
