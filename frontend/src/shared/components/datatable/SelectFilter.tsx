import type { ExtraFilters, TableSource } from "@adapttable/mantine";
import { Select } from "@mantine/core";

export interface SelectFilterProps<TRow> {
  readonly source: TableSource<TRow>;
  readonly filterKey: string;
  readonly label: string;
  readonly placeholder?: string;
  readonly data: ReadonlyArray<{ value: string; label: string }>;
}

function toSelectValue(current: ExtraFilters[string]): string | null {
  if (typeof current === "string") return current;
  if (current == null) return null;
  return String(current);
}

/** Single-select filter bound to `source.extra[filterKey]`. */
export function SelectFilter<TRow>({
  source,
  filterKey,
  label,
  placeholder,
  data,
}: Readonly<SelectFilterProps<TRow>>) {
  const value = toSelectValue(source.extra[filterKey]);

  return (
    <Select
      label={label}
      placeholder={placeholder}
      data={[...data]}
      value={value}
      clearable
      onChange={(next) => source.setExtra(filterKey, next ?? undefined)}
      comboboxProps={{ withinPortal: true }}
    />
  );
}
