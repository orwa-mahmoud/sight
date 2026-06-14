/** Coerce a row field to searchable/filterable text.
 *
 * Only primitives become text — objects and arrays have no meaningful default
 * string form (`[object Object]`), so they yield "" rather than polluting search
 * and filter matches.
 */
export function fieldText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean" || typeof value === "bigint") {
    return String(value);
  }
  return "";
}
