import { Badge, Card, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { IconMessageCircle } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import type { TFunction } from "i18next";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@core/api/client";
import { DataTable, SelectFilter, useFrontendData, type ColumnDef } from "@shared/components/datatable";
import { EmptyState } from "@shared/components/EmptyState";

interface ConversationSummary {
  id: string;
  thread_id: string;
  channel: string;
  last_message_at: string | null;
  created_at: string;
}

interface DailySummary {
  date: string;
  total_messages: number;
  active_conversations: number;
  questions_escalated: number;
}

const CHANNELS = ["whatsapp", "telegram", "email", "web", "owner_dashboard", "api"] as const;

function channelLabel(t: TFunction, channel: string): string {
  return t(`channels.${channel}`, { defaultValue: channel });
}

async function listConversations(): Promise<ConversationSummary[]> {
  const { data } = await api.get<ConversationSummary[]>("/api/v1/conversations");
  return data;
}

async function getDailySummary(): Promise<DailySummary> {
  const { data } = await api.get<DailySummary>("/api/v1/conversations/daily-summary");
  return data;
}

function StatCard({ label, value }: Readonly<{ label: string; value: string | number }>) {
  return (
    <Card withBorder radius="md" p="lg">
      <Text size="xs" tt="uppercase" c="dimmed" fw={600}>
        {label}
      </Text>
      <Text size="xl" fw={700} mt={6}>
        {value}
      </Text>
    </Card>
  );
}

export function ConversationsPage() {
  const { t } = useTranslation();
  const conversationsQuery = useQuery({ queryKey: ["conversations"], queryFn: listConversations });
  const summaryQuery = useQuery({ queryKey: ["daily-summary"], queryFn: getDailySummary });

  const columns = useMemo<ColumnDef<ConversationSummary>[]>(
    () => [
      {
        key: "thread_id",
        header: t("conversations.colThread"),
        sortable: true,
        sortValue: (c) => c.thread_id,
        accessor: (c) => (
          <Text size="sm" fw={500}>
            {c.thread_id.length > 40 ? `${c.thread_id.slice(0, 40)}...` : c.thread_id}
          </Text>
        ),
      },
      {
        key: "channel",
        header: t("conversations.colChannel"),
        accessor: (c) => (
          <Badge color="gray" variant="default">
            {channelLabel(t, c.channel)}
          </Badge>
        ),
      },
      {
        key: "last_message_at",
        header: t("conversations.colLastMessage"),
        sortable: true,
        sortValue: (c) => c.last_message_at ?? "",
        accessor: (c) => (
          <Text size="sm" c="dimmed">
            {c.last_message_at ? dayjs(c.last_message_at).format("MMM D, HH:mm") : "—"}
          </Text>
        ),
      },
      {
        key: "created_at",
        header: t("conversations.colCreated"),
        sortable: true,
        sortValue: (c) => c.created_at,
        accessor: (c) => (
          <Text size="sm" c="dimmed">
            {dayjs(c.created_at).format("MMM D, HH:mm")}
          </Text>
        ),
      },
    ],
    [t],
  );

  const source = useFrontendData<ConversationSummary>({
    data: conversationsQuery.data ?? [],
    columns,
    searchKeys: ["thread_id"],
    isLoading: conversationsQuery.isLoading,
    error: conversationsQuery.error,
    refetch: conversationsQuery.refetch,
  });

  return (
    <Stack>
      <div>
        <Title order={2}>{t("conversations.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("conversations.subtitle")}
        </Text>
      </div>

      {summaryQuery.isSuccess && summaryQuery.data?.total_messages !== undefined && (
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
          <StatCard label={t("conversations.statMessagesToday")} value={summaryQuery.data.total_messages} />
          <StatCard label={t("conversations.statActive")} value={summaryQuery.data.active_conversations} />
          <StatCard label={t("conversations.statEscalated")} value={summaryQuery.data.questions_escalated} />
        </SimpleGrid>
      )}

      <DataTable
        source={source}
        columns={columns}
        rowKey={(c) => c.id}
        tableLabel={t("conversations.title")}
        searchPlaceholder={t("conversations.searchPlaceholder")}
        emptyState={
          <EmptyState
            icon={<IconMessageCircle size={32} stroke={1.4} />}
            title={t("conversations.emptyTitle")}
            description={t("conversations.emptyDesc")}
          />
        }
        filters={
          <SelectFilter
            source={source}
            filterKey="channel"
            label={t("conversations.colChannel")}
            data={CHANNELS.map((c) => ({ value: c, label: channelLabel(t, c) }))}
          />
        }
        filterLabels={{ channel: (v) => `${t("conversations.colChannel")}: ${channelLabel(t, String(v))}` }}
      />
    </Stack>
  );
}
