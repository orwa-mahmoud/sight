import type { MantineColor } from "@mantine/core";
import type { ComponentType, ReactNode } from "react";

export type SortDirection = "asc" | "desc";

export interface CellProps<TRow> {
  readonly row: TRow;
}

/** One column the user sees. `TRow` is the row item type. */
export interface ColumnDef<TRow> {
  /** Unique within the table; also the value sent to the backend as `sortBy`. */
  key: string;
  /** Pre-translated header content. */
  header: ReactNode;
  /** Cell component — define at module level for a stable identity. */
  Cell?: ComponentType<CellProps<TRow>>;
  /** Lightweight cell renderer when a dedicated component is overkill. */
  accessor?: (row: TRow) => ReactNode;
  /** Primitive used by the front-end sort comparator. */
  sortValue?: (row: TRow) => string | number | boolean | null | undefined;
  /** Enable column sort. Off by default. */
  sortable?: boolean;
  width?: number | string;
  align?: "left" | "center" | "right";
  /** Mobile card label. Falls back to `header` when it's a string. */
  mobileLabel?: string;
  hideOnMobile?: boolean;
  hideOnDesktop?: boolean;
}

/** Row-level action — icon buttons on desktop, a button group on mobile cards. */
export interface RowAction<TRow> {
  key: string;
  label: string;
  icon?: ReactNode;
  onClick: (row: TRow) => void;
  color?: MantineColor;
  isDisabled?: (row: TRow) => boolean;
  isHidden?: (row: TRow) => boolean;
  /** When set, the click is routed through a confirmation modal. */
  confirm?: {
    title: string;
    message: (row: TRow) => string;
    confirmLabel: string;
    danger?: boolean;
  };
}

/** Paginated response envelope returned by backend list endpoints. */
export interface PaginatedResponse<TRow> {
  items: TRow[];
  total: number;
  page: number;
  limit: number;
  hasNext: boolean;
}

/** Baseline query params every backend table hook accepts. Callers may extend. */
export interface TableQueryParams {
  page?: number;
  limit?: number;
  search?: string;
  sortBy?: string;
  sortDir?: SortDirection;
}

/** Active "extra" (per-column) filter values, keyed by column key. */
export type ExtraFilters = Record<string, string | string[] | number | undefined>;

/** How pagination renders. `auto` = infinite on mobile, paged on desktop. */
export type PaginationMode = "infinite" | "paged" | "auto";
