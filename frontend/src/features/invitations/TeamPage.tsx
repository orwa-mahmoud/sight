import { Badge, Box, Button, Card, Group, Stack, Text, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconCopy, IconMail, IconTrash, IconUserPlus } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";

import {
  DataTable,
  useFrontendData,
  type CellProps,
  type ColumnDef,
  type RowAction,
} from "@shared/components/datatable";
import { EmptyState } from "@shared/components/EmptyState";
import { useMutationWithNotification } from "@shared/hooks/useMutationWithNotification";

import { createInvitation, listInvitations, revokeInvitation } from "./api";
import type { Invitation } from "./types";

const STATUS_COLOR: Record<string, string> = {
  pending: "blue",
  accepted: "teal",
  rejected: "gray",
  revoked: "red",
};

/** Minimal, regex-free email shape check: `local@domain.tld`, no spaces. */
function isLikelyEmail(value: string): boolean {
  if (value.includes(" ") || value.length < 5) return false;
  const at = value.indexOf("@");
  if (at <= 0 || at !== value.lastIndexOf("@")) return false;
  const dot = value.lastIndexOf(".");
  return dot > at + 1 && dot < value.length - 1;
}

function EmailCell({ row }: Readonly<CellProps<Invitation>>) {
  return (
    <Group gap="xs" wrap="nowrap">
      <IconMail size={14} color="var(--mantine-color-gray-5)" />
      <Text size="sm">{row.email}</Text>
    </Group>
  );
}

function StatusCell({ row }: Readonly<CellProps<Invitation>>) {
  return (
    <Badge color={STATUS_COLOR[row.status] ?? "gray"} variant="light">
      {row.status}
    </Badge>
  );
}

function ExpiresCell({ row }: Readonly<CellProps<Invitation>>) {
  return (
    <Text size="sm" c="dimmed">
      {dayjs(row.expires_at).format("MMM D, YYYY")}
    </Text>
  );
}

export function TeamPage() {
  const { t } = useTranslation();
  const invitationsQuery = useQuery({ queryKey: ["invitations"], queryFn: listInvitations });

  const form = useForm({
    initialValues: { email: "" },
    validate: {
      // Lightweight, regex-free email sanity check (the backend does strict
      // validation). Avoids any catastrophic-backtracking risk from a regex.
      email: (value) => (isLikelyEmail(value) ? null : t("team.invalidEmail")),
    },
  });

  const createMutation = useMutationWithNotification({
    mutationFn: (email: string) => createInvitation(email),
    successMessage: t("team.invited"),
    invalidateKeys: [["invitations"]],
    onSuccess: () => form.reset(),
    onError: (err) => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      const message = status === 400 ? t("team.inviteDuplicate") : t("team.inviteFailed");
      notifications.show({ color: "red", message });
    },
  });

  const revokeMutation = useMutationWithNotification({
    mutationFn: (id: string) => revokeInvitation(id),
    successMessage: t("team.revoked"),
    errorMessage: t("team.actionFailed"),
    invalidateKeys: [["invitations"]],
  });

  const copyLink = useCallback(
    (url: string) => {
      navigator.clipboard
        .writeText(url)
        .then(() => notifications.show({ color: "teal", message: t("team.linkCopied") }))
        .catch(() => notifications.show({ color: "red", message: t("team.copyFailed") }));
    },
    [t],
  );

  const columns = useMemo<ColumnDef<Invitation>[]>(
    () => [
      { key: "email", header: t("team.colEmail"), sortable: true, sortValue: (r) => r.email, Cell: EmailCell },
      { key: "status", header: t("team.colStatus"), Cell: StatusCell },
      {
        key: "expires_at",
        header: t("team.colExpires"),
        sortable: true,
        sortValue: (r) => r.expires_at,
        Cell: ExpiresCell,
      },
    ],
    [t],
  );

  const rowActions = useMemo<RowAction<Invitation>[]>(
    () => [
      {
        key: "copy",
        label: t("team.copyLink"),
        icon: <IconCopy size={16} />,
        isHidden: (r) => r.status !== "pending",
        onClick: (r) => copyLink(r.invite_url),
      },
      {
        key: "revoke",
        label: t("team.revoke"),
        color: "red",
        icon: <IconTrash size={16} />,
        isHidden: (r) => r.status !== "pending",
        onClick: (r) => revokeMutation.mutate(r.id),
        confirm: {
          title: t("team.confirmRevokeTitle"),
          message: (r) => t("team.confirmRevoke", { email: r.email }),
          confirmLabel: t("team.revoke"),
          danger: true,
        },
      },
    ],
    [t, revokeMutation, copyLink],
  );

  const source = useFrontendData<Invitation>({
    data: invitationsQuery.data ?? [],
    columns,
    searchKeys: ["email"],
    isLoading: invitationsQuery.isLoading,
    error: invitationsQuery.error,
    refetch: invitationsQuery.refetch,
  });

  return (
    <Stack>
      <Box>
        <Title order={2}>{t("team.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("team.subtitle")}
        </Text>
      </Box>

      <Card withBorder radius="md" p="md">
        <form onSubmit={form.onSubmit((values) => createMutation.mutate(values.email))}>
          <Group align="flex-end" gap="sm">
            <TextInput
              style={{ flex: 1 }}
              label={t("team.inviteLabel")}
              placeholder={t("team.invitePlaceholder")}
              type="email"
              {...form.getInputProps("email")}
            />
            <Button
              type="submit"
              leftSection={<IconUserPlus size={16} />}
              loading={createMutation.isPending}
            >
              {t("team.invite")}
            </Button>
          </Group>
        </form>
      </Card>

      <DataTable
        source={source}
        columns={columns}
        rowKey={(r) => r.id}
        rowActions={rowActions}
        tableLabel={t("team.title")}
        searchPlaceholder={t("team.searchPlaceholder")}
        emptyState={
          <EmptyState
            icon={<IconMail size={32} stroke={1.4} />}
            title={t("team.emptyTitle")}
            description={t("team.emptyDesc")}
          />
        }
      />
    </Stack>
  );
}
