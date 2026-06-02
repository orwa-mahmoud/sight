/**
 * Stringify an arbitrary cell value for display/search/sort.
 *
 * Objects are JSON-encoded rather than passed to `String()`, which would render
 * the useless `"[object Object]"`. `null`/`undefined` become an empty string.
 * Each branch narrows to a concrete type and calls `.toString()` on it, so no
 * possibly-object value is ever coerced via `String()`.
 */
export function stringifyCellValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "bigint" || typeof value === "boolean") {
    return value.toString();
  }
  if (typeof value === "symbol") return value.toString();
  return ""; // function — not a displayable cell value
}
