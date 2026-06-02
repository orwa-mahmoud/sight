import { Badge, Box, Group, Stack, Text, Title } from "@mantine/core";
import { IconBan, IconBuildingStore, IconCircleCheck } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import {
  DataTable,
  SelectFilter,
  useFrontendData,
  type CellProps,
  type ColumnDef,
  type RowAction,
} from "@shared/components/datatable";
import { EmptyState } from "@shared/components/EmptyState";
import { useMutationWithNotification } from "@shared/hooks/useMutationWithNotification";

import { listTenants, setTenantActive } from "./api";
import type { AdminTenant } from "./types";

const STATUS_COLOR: Record<string, string> = { active: "teal", suspended: "red" };
const STATUSES = ["active", "suspended"] as const;

function NameCell({ row }: Readonly<CellProps<AdminTenant>>) {
  return (
    <Group gap="xs" wrap="nowrap">
      <IconBuildingStore size={14} color="var(--mantine-color-gray-5)" />
      <Text size="sm">{row.name}</Text>
    </Group>
  );
}

function SlugCell({ row }: Readonly<CellProps<AdminTenant>>) {
  return (
    <Text size="sm" c="dimmed">
      {row.slug}
    </Text>
  );
}

function StatusCell({ row }: Readonly<CellProps<AdminTenant>>) {
  return (
    <Badge color={STATUS_COLOR[row.status] ?? "gray"} variant="light">
      {row.status}
    </Badge>
  );
}

function OwnerCell({ row }: Readonly<CellProps<AdminTenant>>) {
  return <Text size="sm">{row.owner_email ?? "—"}</Text>;
}

function UsersCell({ row }: Readonly<CellProps<AdminTenant>>) {
  return <Text size="sm">{row.user_count}</Text>;
}

function DocsCell({ row }: Readonly<CellProps<AdminTenant>>) {
  return <Text size="sm">{row.document_count}</Text>;
}

export function AdminTenantsPage() {
  const { t } = useTranslation();
  const tenantsQuery = useQuery({ queryKey: ["admin", "tenants"], queryFn: listTenants });

  const mutation = useMutationWithNotification({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => setTenantActive(id, active),
    successMessage: t("admin.tenantUpdated"),
    errorMessage: t("admin.actionFailed"),
    invalidateKeys: [["admin", "tenants"]],
  });

  const columns = useMemo<ColumnDef<AdminTenant>[]>(
    () => [
      { key: "name", header: t("admin.colTenant"), sortable: true, sortValue: (r) => r.name, Cell: NameCell },
      { key: "slug", header: t("admin.colSlug"), sortable: true, sortValue: (r) => r.slug, Cell: SlugCell },
      { key: "status", header: t("admin.colStatus"), Cell: StatusCell },
      { key: "owner_email", header: t("admin.colOwner"), Cell: OwnerCell },
      {
        key: "user_count",
        header: t("admin.colUsers"),
        sortable: true,
        sortValue: (r) => r.user_count,
        Cell: UsersCell,
      },
      {
        key: "document_count",
        header: t("admin.colDocs"),
        sortable: true,
        sortValue: (r) => r.document_count,
        Cell: DocsCell,
      },
    ],
    [t],
  );

  const rowActions = useMemo<RowAction<AdminTenant>[]>(
    () => [
      {
        key: "deactivate",
        label: t("admin.deactivateTenant"),
        color: "red",
        icon: <IconBan size={16} />,
        isHidden: (r) => r.status !== "active",
        onClick: (r) => mutation.mutate({ id: r.id, active: false }),
        confirm: {
          title: t("admin.confirmDeactivateTenantTitle"),
          message: (r) => t("admin.confirmDeactivateTenant", { name: r.name }),
          confirmLabel: t("admin.deactivateTenant"),
          danger: true,
        },
      },
      {
        key: "activate",
        label: t("admin.activateTenant"),
        color: "teal",
        icon: <IconCircleCheck size={16} />,
        isHidden: (r) => r.status === "active",
        onClick: (r) => mutation.mutate({ id: r.id, active: true }),
      },
    ],
    [t, mutation],
  );

  const source = useFrontendData<AdminTenant>({
    data: tenantsQuery.data ?? [],
    columns,
    searchKeys: ["name", "slug", "owner_email"],
    isLoading: tenantsQuery.isLoading,
    error: tenantsQuery.error,
    refetch: tenantsQuery.refetch,
  });

  return (
    <Stack>
      <Box>
        <Title order={2}>{t("admin.tenantsTitle")}</Title>
        <Text c="dimmed" size="sm">
          {t("admin.tenantsSubtitle")}
        </Text>
      </Box>

      <DataTable
        source={source}
        columns={columns}
        rowKey={(r) => r.id}
        rowActions={rowActions}
        tableLabel={t("admin.tenantsTitle")}
        searchPlaceholder={t("admin.searchTenants")}
        emptyState={
          <EmptyState
            icon={<IconBuildingStore size={32} stroke={1.4} />}
            title={t("admin.noTenantsTitle")}
            description={t("admin.noTenantsDesc")}
          />
        }
        filters={
          <SelectFilter
            source={source}
            filterKey="status"
            label={t("admin.colStatus")}
            data={STATUSES.map((s) => ({ value: s, label: s }))}
          />
        }
        filterLabels={{ status: (v) => `${t("admin.colStatus")}: ${String(v)}` }}
      />
    </Stack>
  );
}
