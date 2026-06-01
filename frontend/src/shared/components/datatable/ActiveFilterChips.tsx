import { Group, Pill } from "@mantine/core";

export interface FilterChip {
  key: string;
  label: string;
}

export interface ActiveFilterChipsProps {
  readonly chips: readonly FilterChip[];
  readonly onRemove: (key: string) => void;
}

/** Removable chips for the currently active filters. */
export function ActiveFilterChips({ chips, onRemove }: Readonly<ActiveFilterChipsProps>) {
  if (chips.length === 0) return null;
  return (
    <Group gap="xs" wrap="wrap">
      {chips.map((chip) => (
        <Pill key={chip.key} withRemoveButton onRemove={() => onRemove(chip.key)}>
          {chip.label}
        </Pill>
      ))}
    </Group>
  );
}
