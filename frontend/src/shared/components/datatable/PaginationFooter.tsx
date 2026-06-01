import { Button, Group, Pagination, Select, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";

import { PAGE_SIZE_OPTIONS } from "./constants";

export interface PaginationFooterProps {
  readonly mode: "infinite" | "paged";
  readonly page: number;
  readonly limit: number;
  readonly total: number;
  readonly totalPages: number;
  readonly hasNextPage: boolean;
  readonly isFetchingNextPage: boolean;
  readonly onPageChange: (page: number) => void;
  readonly onLimitChange: (limit: number) => void;
  readonly onLoadMore: () => void;
}

export function PaginationFooter({
  mode,
  page,
  limit,
  total,
  totalPages,
  hasNextPage,
  isFetchingNextPage,
  onPageChange,
  onLimitChange,
  onLoadMore,
}: Readonly<PaginationFooterProps>) {
  const { t } = useTranslation();

  if (mode === "infinite") {
    if (!hasNextPage) return null;
    return (
      <Group justify="center" p="sm">
        <Button variant="default" loading={isFetchingNextPage} onClick={onLoadMore}>
          {t("table.loadMore")}
        </Button>
      </Group>
    );
  }

  const from = total === 0 ? 0 : (page - 1) * limit + 1;
  const to = Math.min(page * limit, total);

  return (
    <Group justify="space-between" p="sm" wrap="wrap" gap="sm">
      <Text size="sm" c="dimmed">
        {t("table.rangeOfTotal", { from, to, total })}
      </Text>
      <Group gap="sm">
        <Select
          size="xs"
          w={110}
          aria-label={t("table.perPage")}
          value={String(limit)}
          onChange={(value) => value && onLimitChange(Number(value))}
          data={PAGE_SIZE_OPTIONS.map((n) => ({ value: String(n), label: t("table.perPageN", { n }) }))}
          comboboxProps={{ withinPortal: true }}
        />
        <Pagination
          size="sm"
          total={totalPages}
          value={page}
          onChange={onPageChange}
          withControls
        />
      </Group>
    </Group>
  );
}
