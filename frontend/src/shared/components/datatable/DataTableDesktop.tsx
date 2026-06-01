import { ActionIcon, Group, Table, Text, Tooltip, UnstyledButton } from "@mantine/core";
import { IconChevronDown, IconChevronUp, IconSelector } from "@tabler/icons-react";
import { useRef } from "react";

import { useStaggerIn } from "@shared/animations/stagger";

import { renderCell } from "./renderCell";
import type { ColumnDef, RowAction, SortDirection } from "./types";

export interface DataTableDesktopProps<TRow> {
  readonly columns: ColumnDef<TRow>[];
  readonly rows: readonly TRow[];
  readonly rowKey: (row: TRow) => string;
  readonly rowActions?: RowAction<TRow>[];
  readonly sortBy: string | undefined;
  readonly sortDir: SortDirection | undefined;
  readonly onToggleSort: (key: string) => void;
  readonly emptyText: string;
  readonly tableLabel?: string;
  readonly onRunAction: (action: RowAction<TRow>, row: TRow) => void;
}

export function DataTableDesktop<TRow>({
  columns,
  rows,
  rowKey,
  rowActions,
  sortBy,
  sortDir,
  onToggleSort,
  emptyText,
  tableLabel,
  onRunAction,
}: Readonly<DataTableDesktopProps<TRow>>) {
  const tbodyRef = useRef<HTMLTableSectionElement>(null);
  useStaggerIn(tbodyRef, 'tr[data-stagger="row"]', [rows]);

  const visibleColumns = columns.filter((c) => !c.hideOnDesktop);
  const colSpan = visibleColumns.length + (rowActions && rowActions.length > 0 ? 1 : 0);

  return (
    <Table.ScrollContainer minWidth={480}>
      <Table verticalSpacing="sm" horizontalSpacing="md" highlightOnHover aria-label={tableLabel}>
        <Table.Thead>
          <Table.Tr>
            {visibleColumns.map((col) => {
              const sorted = sortBy === col.key;
              const ariaSort = sorted ? (sortDir === "desc" ? "descending" : "ascending") : undefined;
              return (
                <Table.Th
                  key={col.key}
                  style={{ width: col.width, textAlign: col.align }}
                  aria-sort={ariaSort}
                >
                  {col.sortable ? (
                    <UnstyledButton
                      onClick={() => onToggleSort(col.key)}
                      style={{ display: "inline-flex", alignItems: "center", gap: 4, font: "inherit" }}
                    >
                      <Text span size="sm" fw={600}>
                        {col.header}
                      </Text>
                      {sorted ? (
                        sortDir === "desc" ? (
                          <IconChevronDown size={14} />
                        ) : (
                          <IconChevronUp size={14} />
                        )
                      ) : (
                        <IconSelector size={14} opacity={0.5} />
                      )}
                    </UnstyledButton>
                  ) : (
                    col.header
                  )}
                </Table.Th>
              );
            })}
            {rowActions && rowActions.length > 0 ? <Table.Th w={1} /> : null}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody ref={tbodyRef}>
          {rows.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={colSpan}>
                <Text size="sm" c="dimmed" ta="center" py="xl">
                  {emptyText}
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : (
            rows.map((row) => (
              <Table.Tr key={rowKey(row)} data-stagger="row">
                {visibleColumns.map((col) => (
                  <Table.Td key={col.key} style={{ textAlign: col.align }}>
                    {renderCell(col, row)}
                  </Table.Td>
                ))}
                {rowActions && rowActions.length > 0 ? (
                  <Table.Td>
                    <Group gap={4} justify="flex-end" wrap="nowrap">
                      {rowActions
                        .filter((a) => !a.isHidden?.(row))
                        .map((action) => (
                          <Tooltip key={action.key} label={action.label} withArrow>
                            <ActionIcon
                              variant="subtle"
                              color={action.color ?? "gray"}
                              aria-label={action.label}
                              disabled={action.isDisabled?.(row)}
                              onClick={() => onRunAction(action, row)}
                            >
                              {action.icon ?? <Text size="xs">{action.label}</Text>}
                            </ActionIcon>
                          </Tooltip>
                        ))}
                    </Group>
                  </Table.Td>
                ) : null}
              </Table.Tr>
            ))
          )}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
