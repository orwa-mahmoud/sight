import { TextInput } from "@mantine/core";

import type { TableSource } from "../hooks/TableSource";

export interface TextFilterProps<TRow> {
  readonly source: TableSource<TRow>;
  readonly filterKey: string;
  readonly label: string;
  readonly placeholder?: string;
}

/** Free-text filter bound to `source.extra[filterKey]`. */
export function TextFilter<TRow>({ source, filterKey, label, placeholder }: Readonly<TextFilterProps<TRow>>) {
  const current = source.extra[filterKey];
  const value = typeof current === "string" ? current : "";

  return (
    <TextInput
      label={label}
      placeholder={placeholder}
      value={value}
      onChange={(e) => source.setExtra(filterKey, e.currentTarget.value || undefined)}
    />
  );
}
