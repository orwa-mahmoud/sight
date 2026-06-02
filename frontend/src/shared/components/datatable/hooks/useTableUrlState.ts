import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { DEFAULT_PAGE_SIZE } from "../constants";
import type { ExtraFilters, ExtraFilterValue, SortDirection } from "../types";

const PARAM = {
  search: "q",
  page: "page",
  limit: "page_size",
  sortBy: "sort",
  sortDir: "sort_dir",
} as const;
const FILTER_PREFIX = "filter_";

export interface UseTableUrlStateOptions {
  defaults?: { limit?: number; sortBy?: string; sortDir?: SortDirection };
  numberExtraKeys?: readonly string[];
  arrayExtraKeys?: readonly string[];
}

export interface TableUrlState {
  page: number;
  limit: number;
  search: string;
  sortBy: string | undefined;
  sortDir: SortDirection | undefined;
  extra: ExtraFilters;
  setPage: (next: number) => void;
  setLimit: (next: number) => void;
  setSort: (key: string | undefined, dir?: SortDirection) => void;
  setSearch: (next: string) => void;
  setExtra: (key: string, value: ExtraFilterValue) => void;
  clearAll: () => void;
}

function parseExtra(
  params: URLSearchParams,
  numberKeys: readonly string[],
  arrayKeys: readonly string[],
): ExtraFilters {
  const extra: ExtraFilters = {};
  params.forEach((value, key) => {
    if (!key.startsWith(FILTER_PREFIX) || !value) return;
    const name = key.slice(FILTER_PREFIX.length);
    if (arrayKeys.includes(name)) extra[name] = value.split(",").filter(Boolean);
    else if (numberKeys.includes(name)) extra[name] = Number(value);
    else extra[name] = value;
  });
  return extra;
}

function serializeExtraValue(value: ExtraFilterValue): string {
  if (Array.isArray(value)) return value.join(",");
  if (value === undefined) return "";
  return String(value);
}

/** Reads/writes table state (search, sort, page, per-column filters) to the URL. */
export function useTableUrlState(options: UseTableUrlStateOptions = {}): TableUrlState {
  const { defaults, numberExtraKeys = [], arrayExtraKeys = [] } = options;
  const [params, setParams] = useSearchParams();

  const page = Math.max(1, Number.parseInt(params.get(PARAM.page) ?? "1", 10) || 1);
  const limit = Math.max(
    1,
    Number.parseInt(params.get(PARAM.limit) ?? "", 10) || defaults?.limit || DEFAULT_PAGE_SIZE,
  );
  const search = params.get(PARAM.search) ?? "";
  const sortBy = params.get(PARAM.sortBy) ?? defaults?.sortBy ?? undefined;
  const sortDirRaw = params.get(PARAM.sortDir);
  let sortDir: SortDirection | undefined;
  if (sortBy) sortDir = sortDirRaw === "desc" ? "desc" : (defaults?.sortDir ?? "asc");

  // Depend on serialized key lists, not array identity — callers commonly pass
  // inline arrays, which would otherwise make `extra` a new object every render.
  const numberKeysSig = numberExtraKeys.join(",");
  const arrayKeysSig = arrayExtraKeys.join(",");
  const extra = useMemo(
    () =>
      parseExtra(
        params,
        numberKeysSig ? numberKeysSig.split(",") : [],
        arrayKeysSig ? arrayKeysSig.split(",") : [],
      ),
    [params, numberKeysSig, arrayKeysSig],
  );

  const update = useCallback(
    (mutate: (next: URLSearchParams) => void) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          mutate(next);
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const setPage = useCallback(
    (next: number) => update((p) => (next > 1 ? p.set(PARAM.page, String(next)) : p.delete(PARAM.page))),
    [update],
  );

  const setLimit = useCallback(
    (next: number) =>
      update((p) => {
        p.set(PARAM.limit, String(next));
        p.delete(PARAM.page);
      }),
    [update],
  );

  const setSearch = useCallback(
    (next: string) =>
      update((p) => {
        if (next) p.set(PARAM.search, next);
        else p.delete(PARAM.search);
        p.delete(PARAM.page);
      }),
    [update],
  );

  const setSort = useCallback(
    (key: string | undefined, dir: SortDirection = "asc") =>
      update((p) => {
        if (key) {
          p.set(PARAM.sortBy, key);
          if (dir === "desc") p.set(PARAM.sortDir, "desc");
          else p.delete(PARAM.sortDir);
        } else {
          p.delete(PARAM.sortBy);
          p.delete(PARAM.sortDir);
        }
        p.delete(PARAM.page);
      }),
    [update],
  );

  const setExtra = useCallback(
    (key: string, value: ExtraFilterValue) =>
      update((p) => {
        const name = `${FILTER_PREFIX}${key}`;
        const serialized = serializeExtraValue(value);
        if (serialized) p.set(name, serialized);
        else p.delete(name);
        p.delete(PARAM.page);
      }),
    [update],
  );

  const clearAll = useCallback(
    () =>
      update((p) => {
        // Snapshot keys first — deleting from a live URLSearchParams iterator skips entries.
        const removable = [...p.keys()].filter(
          (key) => key.startsWith(FILTER_PREFIX) || (Object.values(PARAM) as string[]).includes(key),
        );
        for (const key of removable) {
          p.delete(key);
        }
      }),
    [update],
  );

  return {
    page,
    limit,
    search,
    sortBy,
    sortDir,
    extra,
    setPage,
    setLimit,
    setSort,
    setSearch,
    setExtra,
    clearAll,
  };
}
