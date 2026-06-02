import {
  Alert,
  Badge,
  Card,
  Center,
  Drawer,
  Group,
  Loader,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconEye, IconMessageCircle } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import type { TFunction } from "i18next";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@core/api/client";
import {
  DataTable,
  SelectFilter,
  useFrontendData,
  type CellProps,
  type ColumnDef,
  type RowAction,
} from "@shared/components/datatable";
import { EmptyState } from "@shared/components/EmptyState";

interface ConversationSummary {
  id: string;
  thread_id: string;
  channel: string;
  last_message_at: string | null;
  created_at: string;
}

interface ConversationMessage {
  id: string;
  role: string;
  content: string;
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

async function getMessages(id: string): Promise<ConversationMessage[]> {
  const { data } = await api.get<ConversationMessage[]>(`/api/v1/conversations/${id}/messages`);
  return data;
}

function TranscriptDrawer({
  conversationId,
  opened,
  onClose,
}: Readonly<{ conversationId: string | null; opened: boolean; onClose: () => void }>) {
  const { t } = useTranslation();
  const messagesQuery = useQuery({
    queryKey: ["conversation-messages", conversationId],
    queryFn: () => getMessages(conversationId ?? ""),
    enabled: opened && conversationId !== null,
  });

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title={t("conversations.transcript")}
      position="right"
      size="lg"
      padding="lg"
    >
      {messagesQuery.isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}
      {messagesQuery.isError && <Alert color="red">{t("conversations.loadMessagesError")}</Alert>}
      {messagesQuery.isSuccess && messagesQuery.data.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          {t("conversations.noMessages")}
        </Text>
      )}
      {messagesQuery.isSuccess && messagesQuery.data.length > 0 && (
        <Stack gap="sm">
          {messagesQuery.data.map((m) => {
            const isVisitor = m.role === "user";
            return (
              <Card
                key={m.id}
                withBorder
                radius="md"
                p="sm"
                bg={isVisitor ? "gray.0" : "coral.0"}
                ml={isVisitor ? 0 : "auto"}
                mr={isVisitor ? "auto" : 0}
                maw="85%"
              >
                <Group justify="space-between" mb={4} gap="sm">
                  <Text size="xs" fw={600} c={isVisitor ? "dimmed" : "coral.7"}>
                    {isVisitor ? t("conversations.visitor") : t("conversations.assistant")}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {dayjs(m.created_at).format("MMM D, HH:mm")}
                  </Text>
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {m.content}
                </Text>
              </Card>
            );
          })}
        </Stack>
      )}
    </Drawer>
  );
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

// Cell renderers are module-level components (stable identity; keeps them out of
// the page component body per Sonar S6478).
function ThreadCell({ row }: Readonly<CellProps<ConversationSummary>>) {
  return (
    <Text size="sm" fw={500}>
      {row.thread_id.length > 40 ? `${row.thread_id.slice(0, 40)}...` : row.thread_id}
    </Text>
  );
}

function ChannelCell({ row }: Readonly<CellProps<ConversationSummary>>) {
  const { t } = useTranslation();
  return (
    <Badge color="gray" variant="default">
      {channelLabel(t, row.channel)}
    </Badge>
  );
}

function LastMessageCell({ row }: Readonly<CellProps<ConversationSummary>>) {
  return (
    <Text size="sm" c="dimmed">
      {row.last_message_at ? dayjs(row.last_message_at).format("MMM D, HH:mm") : "—"}
    </Text>
  );
}

function CreatedCell({ row }: Readonly<CellProps<ConversationSummary>>) {
  return (
    <Text size="sm" c="dimmed">
      {dayjs(row.created_at).format("MMM D, HH:mm")}
    </Text>
  );
}

export function ConversationsPage() {
  const { t } = useTranslation();
  const conversationsQuery = useQuery({ queryKey: ["conversations"], queryFn: listConversations });
  const summaryQuery = useQuery({ queryKey: ["daily-summary"], queryFn: getDailySummary });

  const [activeId, setActiveId] = useState<string | null>(null);
  const [transcriptOpen, transcript] = useDisclosure(false);

  const rowActions = useMemo<RowAction<ConversationSummary>[]>(
    () => [
      {
        key: "view",
        label: t("conversations.view"),
        icon: <IconEye size={16} />,
        onClick: (c) => {
          setActiveId(c.id);
          transcript.open();
        },
      },
    ],
    [t, transcript],
  );

  const columns = useMemo<ColumnDef<ConversationSummary>[]>(
    () => [
      {
        key: "thread_id",
        header: t("conversations.colThread"),
        sortable: true,
        sortValue: (c) => c.thread_id,
        Cell: ThreadCell,
      },
      { key: "channel", header: t("conversations.colChannel"), Cell: ChannelCell },
      {
        key: "last_message_at",
        header: t("conversations.colLastMessage"),
        sortable: true,
        sortValue: (c) => c.last_message_at ?? "",
        Cell: LastMessageCell,
      },
      {
        key: "created_at",
        header: t("conversations.colCreated"),
        sortable: true,
        sortValue: (c) => c.created_at,
        Cell: CreatedCell,
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
        rowActions={rowActions}
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

      <TranscriptDrawer conversationId={activeId} opened={transcriptOpen} onClose={transcript.close} />
    </Stack>
  );
}
