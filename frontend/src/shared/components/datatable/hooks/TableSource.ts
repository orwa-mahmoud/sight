import type { ExtraFilters, PaginationMode, SortDirection } from "../types";

/**
 * Uniform contract a `<DataTable>` consumes regardless of whether rows come
 * from an API (`useBackendData`) or an in-memory array (`useFrontendData`).
 * The table renders without knowing which fed it.
 */
export interface TableSource<TRow> {
  /* data */
  readonly rows: readonly TRow[];
  readonly total: number;
  readonly isLoading: boolean;
  readonly isFetching: boolean;
  readonly isFetchingNextPage: boolean;
  readonly hasNextPage: boolean;
  fetchNextPage: () => void;
  readonly error: Error | null;
  refetch?: () => Promise<unknown> | void;

  /** Resolved pagination mode (after `"auto"` → mobile/desktop). */
  readonly paginationMode: Exclude<PaginationMode, "auto">;

  /* url/query state (read) */
  readonly page: number;
  readonly limit: number;
  readonly search: string;
  readonly sortBy: string | undefined;
  readonly sortDir: SortDirection | undefined;
  readonly extra: ExtraFilters;

  /* url/query state (write) */
  setPage: (next: number) => void;
  setLimit: (next: number) => void;
  setSort: (key: string | undefined, dir?: SortDirection) => void;
  setSearch: (next: string) => void;
  setExtra: (key: string, value: string | string[] | number | undefined) => void;
  clearAll: () => void;
}
