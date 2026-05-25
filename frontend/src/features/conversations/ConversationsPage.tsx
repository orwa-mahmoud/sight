import {
  Alert,
  Badge,
  Card,
  Center,
  Loader,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { IconMessageCircle } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";

import { api } from "../../core/api/client";

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

async function listConversations(): Promise<ConversationSummary[]> {
  const { data } = await api.get<ConversationSummary[]>("/api/v1/conversations");
  return data;
}

async function getDailySummary(): Promise<DailySummary> {
  const { data } = await api.get<DailySummary>("/api/v1/conversations/daily-summary");
  return data;
}

const CHANNEL_LABEL: Record<string, string> = {
  whatsapp: "WhatsApp",
  telegram: "Telegram",
  email: "Email",
  web: "Web",
  owner_dashboard: "Owner",
  api: "API",
};

function StatCard({ label, value }: Readonly<{ label: string; value: string | number }>) {
  return (
    <Card withBorder radius="md" p="lg">
      <Text size="xs" tt="uppercase" c="dimmed" fw={600}>{label}</Text>
      <Text size="xl" fw={700} mt={6}>{value}</Text>
    </Card>
  );
}

export function ConversationsPage() {
  const conversationsQuery = useQuery({ queryKey: ["conversations"], queryFn: listConversations });
  const summaryQuery = useQuery({ queryKey: ["daily-summary"], queryFn: getDailySummary });

  return (
    <Stack>
      <div>
        <Title order={2}>Conversations</Title>
        <Text c="dimmed" size="sm">All threads between askers and the AI.</Text>
      </div>

      {summaryQuery.isSuccess && (
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
          <StatCard label="Messages today" value={summaryQuery.data.total_messages} />
          <StatCard label="Active conversations" value={summaryQuery.data.active_conversations} />
          <StatCard label="Escalated today" value={summaryQuery.data.questions_escalated} />
        </SimpleGrid>
      )}

      {conversationsQuery.isLoading && <Center py="xl"><Loader /></Center>}
      {conversationsQuery.isError && <Alert color="red">Could not load conversations.</Alert>}

      {conversationsQuery.isSuccess && conversationsQuery.data.length === 0 && (
        <Card withBorder radius="md" p="xl">
          <Center py="xl">
            <Stack align="center" gap="xs">
              <IconMessageCircle size={32} stroke={1.4} />
              <Text fw={500}>No conversations yet.</Text>
              <Text c="dimmed" size="sm">Once askers message, threads appear here.</Text>
            </Stack>
          </Center>
        </Card>
      )}

      {conversationsQuery.isSuccess && conversationsQuery.data.length > 0 && (
        <Card withBorder radius="md" p={0}>
          <Table verticalSpacing="sm" horizontalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Thread</Table.Th>
                <Table.Th>Channel</Table.Th>
                <Table.Th>Last message</Table.Th>
                <Table.Th>Created</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {conversationsQuery.data.map((c) => (
                <Table.Tr key={c.id}>
                  <Table.Td>
                    <Text size="sm" fw={500}>
                      {c.thread_id.length > 40 ? `${c.thread_id.slice(0, 40)}...` : c.thread_id}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge color="gray" variant="default">
                      {CHANNEL_LABEL[c.channel] ?? c.channel}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" c="dimmed">
                      {c.last_message_at ? dayjs(c.last_message_at).format("MMM D, HH:mm") : "—"}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" c="dimmed">{dayjs(c.created_at).format("MMM D, HH:mm")}</Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
}
