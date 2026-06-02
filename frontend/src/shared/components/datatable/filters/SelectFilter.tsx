import { Select } from "@mantine/core";

import type { TableSource } from "../hooks/TableSource";

export interface SelectFilterProps<TRow> {
  readonly source: TableSource<TRow>;
  readonly filterKey: string;
  readonly label: string;
  readonly placeholder?: string;
  readonly data: ReadonlyArray<{ value: string; label: string }>;
}

/** Single-select filter bound to `source.extra[filterKey]`. */
export function SelectFilter<TRow>({
  source,
  filterKey,
  label,
  placeholder,
  data,
}: Readonly<SelectFilterProps<TRow>>) {
  const current = source.extra[filterKey];
  const value = typeof current === "string" ? current : current == null ? null : String(current);

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
