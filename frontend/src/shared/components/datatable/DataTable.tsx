import { Alert, Box, Button, Card, Drawer, Group, Indicator, Stack, TextInput } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { IconFilter, IconSearch } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { TableSkeleton } from "@shared/components/TableSkeleton";
import { useDebounce } from "@shared/hooks/useDebounce";
import { openConfirm } from "@shared/utils/confirm";

import { ActiveFilterChips, type FilterChip } from "./ActiveFilterChips";
import { MOBILE_MEDIA_QUERY, SEARCH_DEBOUNCE_MS } from "./constants";
import { DataTableDesktop } from "./DataTableDesktop";
import { DataTableMobile } from "./DataTableMobile";
import type { TableSource } from "./hooks/TableSource";
import { PaginationFooter } from "./PaginationFooter";
import type { ColumnDef, RowAction } from "./types";

export interface DataTableProps<TRow> {
  readonly source: TableSource<TRow>;
  readonly columns: ColumnDef<TRow>[];
  readonly rowKey: (row: TRow) => string;
  readonly rowActions?: RowAction<TRow>[];
  readonly searchable?: boolean;
  readonly searchPlaceholder?: string;
  readonly emptyState?: ReactNode;
  readonly emptyText?: string;
  readonly tableLabel?: string;
  /** Toolbar slot (e.g. an "Add" button) shown on the right of the search row. */
  readonly toolbar?: ReactNode;
  /** Filter widgets rendered inside the drawer. */
  readonly filters?: ReactNode;
  /** Per-key chip label resolvers; produce one removable chip per active filter. */
  readonly filterLabels?: Readonly<Record<string, (value: string | string[] | number) => string>>;
}

export function DataTable<TRow>({
  source,
  columns,
  rowKey,
  rowActions,
  searchable = true,
  searchPlaceholder,
  emptyState,
  emptyText,
  tableLabel,
  toolbar,
  filters,
  filterLabels,
}: Readonly<DataTableProps<TRow>>) {
  const { t } = useTranslation();
  const isMobile = useMediaQuery(MOBILE_MEDIA_QUERY) ?? false;
  const [drawerOpen, drawer] = useDisclosure(false);

  // Local search input with a debounced flush to the source (single writer).
  // External changes (back button / deep link) are mirrored during render via
  // the documented "adjust state while rendering" pattern.
  const [searchInput, setSearchInput] = useState(source.search);
  const [prevSearch, setPrevSearch] = useState(source.search);
  if (source.search !== prevSearch) {
    setPrevSearch(source.search);
    setSearchInput(source.search);
  }
  const debounced = useDebounce(searchInput, SEARCH_DEBOUNCE_MS);
  useEffect(() => {
    if (debounced.trim() !== source.search) source.setSearch(debounced.trim());
  }, [debounced, source]);

  const toggleSort = (key: string) => {
    if (source.sortBy !== key) source.setSort(key, "asc");
    else if (source.sortDir === "asc") source.setSort(key, "desc");
    else source.setSort(undefined);
  };

  const runAction = (action: RowAction<TRow>, row: TRow) => {
    if (action.confirm) {
      openConfirm({
        title: action.confirm.title,
        message: action.confirm.message(row),
        confirmLabel: action.confirm.confirmLabel,
        cancelLabel: t("common.cancel"),
        danger: action.confirm.danger,
        onConfirm: () => action.onClick(row),
      });
    } else {
      action.onClick(row);
    }
  };

  const chips = useMemo<FilterChip[]>(() => {
    if (!filterLabels) return [];
    return Object.entries(source.extra)
      .filter(([key, value]) => filterLabels[key] && value !== undefined && value !== "")
      .map(([key, value]) => ({ key, label: filterLabels[key]!(value as string | string[] | number) }));
  }, [source.extra, filterLabels]);

  const totalPages = Math.max(1, Math.ceil(source.total / Math.max(source.limit, 1)));

  let body: ReactNode;
  if (source.isLoading) {
    body = <TableSkeleton />;
  } else if (source.error) {
    body = (
      <Alert color="red" title={t("table.loadError")}>
        <Group justify="space-between">
          <span>{t("common.retry")}</span>
          {source.refetch ? (
            <Button size="xs" variant="light" color="red" onClick={() => void source.refetch?.()}>
              {t("table.retryAction")}
            </Button>
          ) : null}
        </Group>
      </Alert>
    );
  } else if (source.rows.length === 0 && emptyState) {
    body = emptyState;
  } else {
    const resolvedEmpty = emptyText ?? t("common.noResults");
    body = (
      <Card withBorder radius="md" p={0}>
        {isMobile ? (
          <Box p="sm">
            <DataTableMobile
              columns={columns}
              rows={source.rows}
              rowKey={rowKey}
              rowActions={rowActions}
              emptyText={resolvedEmpty}
              onRunAction={runAction}
            />
          </Box>
        ) : (
          <DataTableDesktop
            columns={columns}
            rows={source.rows}
            rowKey={rowKey}
            rowActions={rowActions}
            sortBy={source.sortBy}
            sortDir={source.sortDir}
            onToggleSort={toggleSort}
            emptyText={resolvedEmpty}
            tableLabel={tableLabel}
            onRunAction={runAction}
          />
        )}
        <PaginationFooter
          mode={source.paginationMode}
          page={source.page}
          limit={source.limit}
          total={source.total}
          totalPages={totalPages}
          hasNextPage={source.hasNextPage}
          isFetchingNextPage={source.isFetchingNextPage}
          onPageChange={source.setPage}
          onLimitChange={source.setLimit}
          onLoadMore={source.fetchNextPage}
        />
      </Card>
    );
  }

  return (
    <Stack gap="sm">
      <Group justify="space-between" gap="sm" wrap="wrap">
        <Group gap="sm" wrap="wrap">
          {searchable ? (
            <TextInput
              leftSection={<IconSearch size={16} />}
              placeholder={searchPlaceholder ?? t("common.search")}
              value={searchInput}
              onChange={(e) => setSearchInput(e.currentTarget.value)}
              w={260}
              aria-label={t("common.search")}
            />
          ) : null}
          {filters ? (
            <Indicator label={chips.length} disabled={chips.length === 0} size={16} color="coral">
              <Button variant="default" leftSection={<IconFilter size={16} />} onClick={drawer.open}>
                {t("common.filters")}
              </Button>
            </Indicator>
          ) : null}
        </Group>
        {toolbar}
      </Group>

      {chips.length > 0 ? <ActiveFilterChips chips={chips} onRemove={(key) => source.setExtra(key, undefined)} /> : null}

      {body}

      {filters ? (
        <Drawer opened={drawerOpen} onClose={drawer.close} title={t("common.filters")} position="right" padding="lg">
          <Stack gap="md">
            {filters}
            <Group justify="space-between" mt="md">
              <Button variant="subtle" color="gray" onClick={source.clearAll} disabled={chips.length === 0}>
                {t("common.clearAll")}
              </Button>
              <Button onClick={drawer.close}>{t("common.applyFilters")}</Button>
            </Group>
          </Stack>
        </Drawer>
      ) : null}
    </Stack>
  );
}
