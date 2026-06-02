import type { ReactNode } from "react";

import { stringifyCellValue } from "./stringify";
import type { ColumnDef } from "./types";

/** Resolve a column's content for a row: Cell component → accessor → raw value. */
export function renderCell<TRow>(column: ColumnDef<TRow>, row: TRow): ReactNode {
  if (column.Cell) return <column.Cell row={row} />;
  if (column.accessor) return column.accessor(row);
  const value =
    typeof row === "object" && row !== null ? (row as Record<string, unknown>)[column.key] : undefined;
  return stringifyCellValue(value);
}
