import { Box, Button, Card, Group, Stack, Text } from "@mantine/core";
import { useRef } from "react";

import { useStaggerIn } from "@shared/animations/stagger";

import { renderCell } from "./renderCell";
import type { ColumnDef, RowAction } from "./types";

export interface DataTableMobileProps<TRow> {
  readonly columns: ColumnDef<TRow>[];
  readonly rows: readonly TRow[];
  readonly rowKey: (row: TRow) => string;
  readonly rowActions?: RowAction<TRow>[];
  readonly emptyText: string;
  readonly onRunAction: (action: RowAction<TRow>, row: TRow) => void;
}

function labelFor<TRow>(column: ColumnDef<TRow>): string {
  if (column.mobileLabel) return column.mobileLabel;
  return typeof column.header === "string" ? column.header : column.key;
}

export function DataTableMobile<TRow>({
  columns,
  rows,
  rowKey,
  rowActions,
  emptyText,
  onRunAction,
}: Readonly<DataTableMobileProps<TRow>>) {
  const listRef = useRef<HTMLDivElement>(null);
  useStaggerIn(listRef, '[data-stagger="card"]', [rows]);

  const visibleColumns = columns.filter((c) => !c.hideOnMobile);

  if (rows.length === 0) {
    return (
      <Text size="sm" c="dimmed" ta="center" py="xl">
        {emptyText}
      </Text>
    );
  }

  return (
    <Stack gap="sm" ref={listRef}>
      {rows.map((row) => (
        <Card key={rowKey(row)} withBorder radius="md" p="md" data-stagger="card">
          <Stack gap={6}>
            {visibleColumns.map((col) => (
              <Group key={col.key} justify="space-between" gap="md" wrap="nowrap">
                <Text size="xs" c="dimmed" fw={600} tt="uppercase">
                  {labelFor(col)}
                </Text>
                <Box style={{ textAlign: "end", minWidth: 0 }}>{renderCell(col, row)}</Box>
              </Group>
            ))}
            {rowActions && rowActions.length > 0 ? (
              <Group gap="xs" mt={4}>
                {rowActions
                  .filter((a) => !a.isHidden?.(row))
                  .map((action) => (
                    <Button
                      key={action.key}
                      size="xs"
                      variant="light"
                      color={action.color ?? "gray"}
                      leftSection={action.icon}
                      disabled={action.isDisabled?.(row)}
                      onClick={() => onRunAction(action, row)}
                    >
                      {action.label}
                    </Button>
                  ))}
              </Group>
            ) : null}
          </Stack>
        </Card>
      ))}
    </Stack>
  );
}
