import { useMediaQuery } from "@mantine/hooks";
import type { InfiniteData, UseInfiniteQueryResult } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";

import { MOBILE_MEDIA_QUERY } from "../constants";
import type { PaginatedResponse, PaginationMode, TableQueryParams } from "../types";
import type { TableSource } from "./TableSource";
import { useTableUrlState, type UseTableUrlStateOptions } from "./useTableUrlState";

export type PageSelector<TRow, TPage> = (page: TPage) => { items: readonly TRow[]; total?: number };

export interface UseBackendDataOptions<TRow, TParams extends TableQueryParams, TPage> {
  /** Caller's hook, MUST be built on `useInfiniteQuery`. Receives merged params. */
  usePaginatedQuery: (params: Partial<TParams>) => UseInfiniteQueryResult<InfiniteData<TPage>, Error>;
  /** Defaults to reading a {@link PaginatedResponse} envelope. */
  selectPage?: PageSelector<TRow, TPage>;
  baseParams?: Partial<TParams>;
  paginationMode?: PaginationMode;
  urlState?: UseTableUrlStateOptions;
}

const DEFAULT_SELECTOR: PageSelector<unknown, PaginatedResponse<unknown>> = (page) => ({
  items: page.items,
  total: page.total,
});

/** Server-paginated {@link TableSource} built from a caller's infinite query. */
export function useBackendData<TRow, TParams extends TableQueryParams, TPage = PaginatedResponse<TRow>>(
  options: UseBackendDataOptions<TRow, TParams, TPage>,
): TableSource<TRow> {
  const { usePaginatedQuery, selectPage, baseParams, paginationMode = "auto" } = options;

  const isMobile = useMediaQuery(MOBILE_MEDIA_QUERY) ?? false;
  const autoMode: "infinite" | "paged" = isMobile ? "infinite" : "paged";
  const resolvedMode: "infinite" | "paged" = paginationMode === "auto" ? autoMode : paginationMode;
  const paged = resolvedMode === "paged";

  const state = useTableUrlState(options.urlState);
  const { page, limit, search, sortBy, sortDir, extra } = state;

  const params = useMemo(() => {
    // baseParams first, then user filters (extra) and table state win.
    const merged: Record<string, unknown> = { ...baseParams, ...extra };
    merged.page = page;
    merged.limit = limit;
    merged.search = search || undefined;
    merged.sortBy = sortBy;
    merged.sortDir = sortDir;
    return merged as Partial<TParams>;
  }, [extra, baseParams, page, limit, search, sortBy, sortDir]);

  const query = usePaginatedQuery(params);
  const selector = selectPage ?? (DEFAULT_SELECTOR as PageSelector<TRow, TPage>);

  const { rows, total } = useMemo(() => {
    const pages = query.data?.pages;
    if (!pages || pages.length === 0) return { rows: [] as readonly TRow[], total: 0 };
    const project = selector;
    if (paged) {
      const lastPage = pages.at(-1)!;
      const projected = project(lastPage);
      return { rows: projected.items, total: projected.total ?? projected.items.length };
    }
    const acc: TRow[] = [];
    let lastTotal = 0;
    for (const pg of pages) {
      const projected = project(pg);
      acc.push(...projected.items);
      if (projected.total !== undefined) lastTotal = projected.total;
    }
    return { rows: acc as readonly TRow[], total: lastTotal };
  }, [query.data, paged, selector]);

  const fetchNextPage = useCallback(() => {
    if (query.hasNextPage && !query.isFetchingNextPage) {
      query.fetchNextPage().catch(() => undefined);
    }
  }, [query]);

  return {
    rows,
    total,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage ?? false,
    fetchNextPage,
    error: query.error ?? null,
    refetch: query.refetch,
    paginationMode: resolvedMode,
    // Clamp a stale/oversized URL page (e.g. a filter shrank the result set) so
    // the paged control and the next request never point past the last page.
    page: paged && total > 0 ? Math.min(page, Math.max(1, Math.ceil(total / limit))) : page,
    limit,
    search,
    sortBy,
    sortDir,
    extra,
    setPage: state.setPage,
    setLimit: state.setLimit,
    setSort: state.setSort,
    setSearch: state.setSearch,
    setExtra: state.setExtra,
    clearAll: state.clearAll,
  };
}
