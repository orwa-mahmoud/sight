import { getLabels } from "@adapttable/i18n";
import {
  DataTable as AdaptDataTable,
  type ConfirmHandler,
  type DataTableProps as AdaptDataTableProps,
} from "@adapttable/mantine";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { useLanguage } from "@shared/i18n/useLanguage";
import { openConfirm } from "@shared/utils/confirm";

export interface DataTableProps<TRow>
  extends Omit<
    AdaptDataTableProps<TRow>,
    "confirm" | "labels" | "dir" | "locale" | "slots" | "hideSearch" | "filtersMode" | "animate"
  > {
  /** @default true */
  searchable?: boolean;
  emptyState?: ReactNode;
  emptyText?: string;
  labels?: AdaptDataTableProps<TRow>["labels"];
  locale?: AdaptDataTableProps<TRow>["locale"];
  dir?: AdaptDataTableProps<TRow>["dir"];
}

const tableConfirm: ConfirmHandler = ({
  title,
  message,
  confirmLabel,
  cancelLabel,
  danger,
  onConfirm,
}) => {
  openConfirm({ title, message, confirmLabel, cancelLabel, danger, onConfirm });
};

export function DataTable<TRow>({
  searchable = true,
  emptyState,
  emptyText,
  labels,
  locale,
  dir,
  ...props
}: Readonly<DataTableProps<TRow>>) {
  const { t } = useTranslation();
  const { dir: languageDir, language } = useLanguage();

  // Only override the genuinely-empty ("no data") state with the caller's
  // onboarding empty-state. When a search/filter is active but matched nothing,
  // leave the library's "no results" variant — with its "Clear all" recovery
  // button — intact, instead of showing a misleading "nothing here yet" message.
  const hasActiveQuery =
    (props.source?.search?.length ?? 0) > 0 || Object.keys(props.source?.extra ?? {}).length > 0;
  const emptySlot = emptyState && !hasActiveQuery ? emptyState : undefined;

  const resolvedLabels = {
    ...getLabels(locale ?? language),
    ...labels,
    ...(emptyText ? { noData: emptyText } : undefined),
    cancel: t("common.cancel"),
    filters: t("common.filters"),
    clearAll: t("common.clearAll"),
    applyFilters: t("common.applyFilters"),
    errorTitle: t("table.loadError"),
    retry: t("table.retryAction"),
    loadMore: t("table.loadMore"),
    showing: ({ from, to, total }: { from: number; to: number; total: number }) =>
      t("table.rangeOfTotal", { from, to, total }),
    rowsPerPage: t("table.perPage"),
  };

  return (
    <AdaptDataTable
      {...props}
      dir={dir ?? languageDir}
      locale={locale ?? language}
      labels={resolvedLabels}
      confirm={tableConfirm}
      hideSearch={!searchable}
      filtersMode="drawer"
      animate
      slots={emptySlot ? { empty: emptySlot } : undefined}
    />
  );
}
