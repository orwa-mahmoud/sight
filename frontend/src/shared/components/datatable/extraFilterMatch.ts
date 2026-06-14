import type { ExtraFilters } from "@adapttable/mantine";

import { fieldText } from "./cellText";

function fieldString(row: unknown, key: string): string {
  if (typeof row !== "object" || row === null) return "";
  return fieldText((row as Record<string, unknown>)[key]).toLowerCase();
}

/** Match `source.extra` filter keys against row object fields (client-side tables). */
export function matchesExtraFilters<T>(row: T, extra: ExtraFilters): boolean {
  return Object.entries(extra).every(([key, value]) => {
    if (value === undefined || value === "" || (Array.isArray(value) && value.length === 0)) {
      return true;
    }
    const field = fieldString(row, key);
    if (Array.isArray(value)) {
      return value.some((v) => field === String(v).toLowerCase());
    }
    return field === String(value).toLowerCase();
  });
}
