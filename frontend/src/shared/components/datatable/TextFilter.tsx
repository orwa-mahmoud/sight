import type { TableSource } from "@adapttable/mantine";
import { TextInput } from "@mantine/core";

export interface TextFilterProps<TRow> {
  readonly source: TableSource<TRow>;
  readonly filterKey: string;
  readonly label: string;
  readonly placeholder?: string;
}

/** Text filter bound to `source.extra[filterKey]`. */
export function TextFilter<TRow>({
  source,
  filterKey,
  label,
  placeholder,
}: Readonly<TextFilterProps<TRow>>) {
  const raw = source.extra[filterKey];
  let value = "";
  if (typeof raw === "string") value = raw;
  else if (raw != null) value = String(raw);

  return (
    <TextInput
      label={label}
      placeholder={placeholder}
      value={value}
      onChange={(e) => source.setExtra(filterKey, e.currentTarget.value || undefined)}
    />
  );
}
