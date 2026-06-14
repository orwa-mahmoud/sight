import {
  useFrontendData as useAdaptFrontendData,
  type ExtraFilters,
  type TableSource,
  type UseFrontendDataOptions as AdaptUseFrontendDataOptions,
  type UseTableUrlStateOptions,
} from "@adapttable/mantine";
import { useMemo } from "react";

import { matchesExtraFilters } from "./extraFilterMatch";
import { useReactRouterUrlAdapter } from "./useReactRouterUrlAdapter";

export interface UseFrontendDataOptions<TRow>
  extends Omit<AdaptUseFrontendDataOptions<TRow>, "adapter" | "filterFn" | "getSearchText"> {
  searchKeys?: readonly string[];
  urlState?: Omit<UseTableUrlStateOptions, "adapter">;
  filterFn?: (row: TRow, extra: ExtraFilters) => boolean;
  getSearchText?: (row: TRow) => string;
}

function searchTextFromKeys<TRow>(row: TRow, keys: readonly string[]): string {
  return keys
    .map((key) => {
      if (typeof row !== "object" || row === null) return "";
      const value = (row as Record<string, unknown>)[key];
      if (value == null) return "";
      return String(value);
    })
    .join(" ")
    .toLowerCase();
}

export function useFrontendData<TRow>(options: UseFrontendDataOptions<TRow>): TableSource<TRow> {
  const routerAdapter = useReactRouterUrlAdapter();
  const { searchKeys, urlState, filterFn, getSearchText, ...rest } = options;

  const resolvedSearchText = useMemo(() => {
    if (getSearchText) return getSearchText;
    if (searchKeys) return (row: TRow) => searchTextFromKeys(row, searchKeys);
    return undefined;
  }, [getSearchText, searchKeys]);

  const resolvedFilterFn = useMemo(
    () => filterFn ?? ((row: TRow, extra: ExtraFilters) => matchesExtraFilters(row, extra)),
    [filterFn],
  );

  return useAdaptFrontendData({
    ...rest,
    ...urlState,
    adapter: routerAdapter,
    getSearchText: resolvedSearchText,
    filterFn: resolvedFilterFn,
  });
}
