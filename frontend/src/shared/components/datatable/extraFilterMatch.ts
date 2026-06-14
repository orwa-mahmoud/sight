import type { ExtraFilters } from "@adapttable/mantine";

function fieldString(row: unknown, key: string): string {
  if (typeof row !== "object" || row === null) return "";
  const value = (row as Record<string, unknown>)[key];
  if (value == null) return "";
  return String(value).toLowerCase();
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
