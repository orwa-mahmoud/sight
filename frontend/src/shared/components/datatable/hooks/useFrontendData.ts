import { useMediaQuery } from "@mantine/hooks";
import { useMemo, useState } from "react";

import { MOBILE_MEDIA_QUERY } from "../constants";
import { stringifyCellValue } from "../stringify";
import type { ColumnDef, ExtraFilters, PaginationMode } from "../types";
import type { TableSource } from "./TableSource";
import { useTableUrlState, type UseTableUrlStateOptions } from "./useTableUrlState";

export interface UseFrontendDataOptions<TRow> {
  /** The full in-memory dataset (already fetched). */
  data: readonly TRow[];
  columns: ColumnDef<TRow>[];
  /** Object keys to search; defaults to every column `key`. */
  searchKeys?: readonly string[];
  paginationMode?: PaginationMode;
  /** Surface the owning query's status so the table can show loading/error. */
  isLoading?: boolean;
  error?: Error | null;
  refetch?: () => Promise<unknown> | void;
  urlState?: UseTableUrlStateOptions;
}

function fieldString(row: unknown, key: string): string {
  if (typeof row !== "object" || row === null) return "";
  const value = (row as Record<string, unknown>)[key];
  return stringifyCellValue(value).toLowerCase();
}

function matchesSearch<T>(row: T, search: string, keys: readonly string[]): boolean {
  if (!search.trim()) return true;
  const q = search.trim().toLowerCase();
  return keys.some((k) => fieldString(row, k).includes(q));
}

function matchesExtra<T>(row: T, extra: ExtraFilters): boolean {
  return Object.entries(extra).every(([key, value]) => {
    if (value === undefined || value === "" || (Array.isArray(value) && value.length === 0)) return true;
    const field = fieldString(row, key);
    if (Array.isArray(value)) return value.some((v) => field === String(v).toLowerCase());
    return field === String(value).toLowerCase();
  });
}

function compare(a: unknown, b: unknown): number {
  const an = a === null || a === undefined;
  const bn = b === null || b === undefined;
  if (an && bn) return 0;
  if (an) return 1;
  if (bn) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return stringifyCellValue(a).localeCompare(stringifyCellValue(b));
}

/** In-memory {@link TableSource}: client-side search / filter / sort / paginate. */
export function useFrontendData<TRow>(options: UseFrontendDataOptions<TRow>): TableSource<TRow> {
  const {
    data,
    columns,
    searchKeys,
    paginationMode = "auto",
    isLoading = false,
    error = null,
    refetch,
  } = options;

  const isMobile = useMediaQuery(MOBILE_MEDIA_QUERY) ?? false;
  const autoMode: "infinite" | "paged" = isMobile ? "infinite" : "paged";
  const resolvedMode: "infinite" | "paged" = paginationMode === "auto" ? autoMode : paginationMode;

  const state = useTableUrlState(options.urlState);
  const { page, limit, search, sortBy, sortDir, extra } = state;

  const keysToSearch = useMemo(
    () => (searchKeys?.length ? searchKeys : columns.map((c) => c.key)),
    [searchKeys, columns],
  );

  const filteredSorted = useMemo(() => {
    const filtered = data.filter(
      (row) => matchesSearch(row, search, keysToSearch) && matchesExtra(row, extra),
    );
    if (!sortBy) return filtered;
    const col = columns.find((c) => c.key === sortBy);
    const getVal = col?.sortValue
      ? (row: TRow) => col.sortValue!(row)
      : (row: TRow) =>
          typeof row === "object" && row !== null ? (row as Record<string, unknown>)[sortBy] : undefined;
    const sorted = [...filtered].sort((a, b) => compare(getVal(a), getVal(b)));
    if (sortDir === "desc") sorted.reverse();
    return sorted;
  }, [data, search, keysToSearch, extra, sortBy, sortDir, columns]);

  const total = filteredSorted.length;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  // Infinite mode accumulates pages into one visible slice. Reset the count
  // whenever the query shape changes — done during render (React's documented
  // "adjust state while rendering" pattern) rather than in an effect.
  const filterKey = `${search}|${sortBy}|${sortDir}|${JSON.stringify(extra)}|${limit}`;
  const [loadedPages, setLoadedPages] = useState(1);
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey);
    setLoadedPages(1);
  }

  const rows = useMemo(() => {
    if (resolvedMode === "paged") {
      const safePage = Math.min(page, totalPages);
      const start = (safePage - 1) * limit;
      return filteredSorted.slice(start, start + limit);
    }
    return filteredSorted.slice(0, loadedPages * limit);
  }, [resolvedMode, filteredSorted, page, totalPages, limit, loadedPages]);

  const hasNextPage = resolvedMode === "infinite" && loadedPages * limit < total;

  return {
    rows,
    total,
    isLoading,
    isFetching: isLoading,
    isFetchingNextPage: false,
    hasNextPage,
    fetchNextPage: () => setLoadedPages((n) => n + 1),
    error,
    refetch,
    paginationMode: resolvedMode,
    page: Math.min(page, totalPages),
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
