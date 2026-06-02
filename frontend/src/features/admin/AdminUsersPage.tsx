import { Badge, Box, Group, Stack, Text, Title } from "@mantine/core";
import { IconBan, IconCircleCheck, IconShieldLock, IconUser } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "@auth/useAuth";
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

import { listUsers, setUserActive } from "./api";
import type { AdminUser } from "./types";

const STATUSES = ["active", "inactive"] as const;

function EmailCell({ row }: Readonly<CellProps<AdminUser>>) {
  return (
    <Group gap="xs" wrap="nowrap">
      {row.is_platform_admin ? (
        <IconShieldLock size={14} color="var(--mantine-color-coral-6)" />
      ) : (
        <IconUser size={14} color="var(--mantine-color-gray-5)" />
      )}
      <Text size="sm">{row.email}</Text>
    </Group>
  );
}

function NameCell({ row }: Readonly<CellProps<AdminUser>>) {
  return <Text size="sm">{row.full_name ?? "—"}</Text>;
}

function TenantCell({ row }: Readonly<CellProps<AdminUser>>) {
  return (
    <Text size="sm" c="dimmed">
      {row.tenant_name ?? "—"}
      {row.role ? ` (${row.role})` : ""}
    </Text>
  );
}

function StatusCell({ row }: Readonly<CellProps<AdminUser>>) {
  return (
    <Group gap={6} wrap="nowrap">
      <Badge color={row.is_active ? "teal" : "red"} variant="light">
        {row.is_active ? "active" : "inactive"}
      </Badge>
      {row.is_platform_admin && (
        <Badge color="coral" variant="light">
          admin
        </Badge>
      )}
    </Group>
  );
}

export function AdminUsersPage() {
  const { t } = useTranslation();
  const { user: currentUser } = useAuth();
  const usersQuery = useQuery({ queryKey: ["admin", "users"], queryFn: listUsers });

  const mutation = useMutationWithNotification({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => setUserActive(id, active),
    successMessage: t("admin.userUpdated"),
    errorMessage: t("admin.actionFailed"),
    invalidateKeys: [["admin", "users"]],
  });

  const columns = useMemo<ColumnDef<AdminUser>[]>(
    () => [
      { key: "email", header: t("admin.colEmail"), sortable: true, sortValue: (r) => r.email, Cell: EmailCell },
      { key: "full_name", header: t("admin.colName"), Cell: NameCell },
      { key: "tenant_name", header: t("admin.colTenant"), Cell: TenantCell },
      { key: "is_active", header: t("admin.colStatus"), Cell: StatusCell },
    ],
    [t],
  );

  const rowActions = useMemo<RowAction<AdminUser>[]>(
    () => [
      {
        key: "deactivate",
        label: t("admin.deactivateUser"),
        color: "red",
        icon: <IconBan size={16} />,
        isHidden: (r) => !r.is_active,
        // Cannot disable yourself or another platform admin (lockout guard,
        // mirrored from the backend so the UI doesn't offer a doomed action).
        isDisabled: (r) => r.id === currentUser?.id || r.is_platform_admin,
        onClick: (r) => mutation.mutate({ id: r.id, active: false }),
        confirm: {
          title: t("admin.confirmDeactivateUserTitle"),
          message: (r) => t("admin.confirmDeactivateUser", { email: r.email }),
          confirmLabel: t("admin.deactivateUser"),
          danger: true,
        },
      },
      {
        key: "activate",
        label: t("admin.activateUser"),
        color: "teal",
        icon: <IconCircleCheck size={16} />,
        isHidden: (r) => r.is_active,
        onClick: (r) => mutation.mutate({ id: r.id, active: true }),
      },
    ],
    [t, mutation, currentUser?.id],
  );

  const source = useFrontendData<AdminUser>({
    data: usersQuery.data ?? [],
    columns,
    searchKeys: ["email", "full_name", "tenant_name"],
    isLoading: usersQuery.isLoading,
    error: usersQuery.error,
    refetch: usersQuery.refetch,
  });

  return (
    <Stack>
      <Box>
        <Title order={2}>{t("admin.usersTitle")}</Title>
        <Text c="dimmed" size="sm">
          {t("admin.usersSubtitle")}
        </Text>
      </Box>

      <DataTable
        source={source}
        columns={columns}
        rowKey={(r) => r.id}
        rowActions={rowActions}
        tableLabel={t("admin.usersTitle")}
        searchPlaceholder={t("admin.searchUsers")}
        emptyState={
          <EmptyState
            icon={<IconUser size={32} stroke={1.4} />}
            title={t("admin.noUsersTitle")}
            description={t("admin.noUsersDesc")}
          />
        }
        filters={
          <SelectFilter
            source={source}
            filterKey="is_active"
            label={t("admin.colStatus")}
            data={STATUSES.map((s) => ({ value: s === "active" ? "true" : "false", label: s }))}
          />
        }
        filterLabels={{ is_active: (v) => `${t("admin.colStatus")}: ${v === "true" ? "active" : "inactive"}` }}
      />
    </Stack>
  );
}
