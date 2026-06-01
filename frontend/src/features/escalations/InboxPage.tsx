import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  ScrollArea,
  SegmentedControl,
  Stack,
  Text,
  Textarea,
  Title,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconArchive, IconRefresh, IconRobot, IconSend } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useState } from "react";

import { closeQuestion, listQuestions, replyToQuestion } from "./api";
import type { Question, QuestionStatus } from "./types";

const STATUS_COLOR: Record<QuestionStatus, string> = {
  submitted: "coral",
  resolved: "teal",
  closed: "gray",
};

const CHANNEL_LABEL: Record<string, string> = {
  whatsapp: "WhatsApp",
  telegram: "Telegram",
  email: "Email",
  web: "Web",
  owner_dashboard: "Owner",
  api: "API",
};

export function InboxPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<QuestionStatus | "all">("submitted");
  const [active, setActive] = useState<Question | null>(null);
  const [replyText, setReplyText] = useState("");
  const [opened, { open, close }] = useDisclosure(false);

  const status = filter === "all" ? undefined : filter;
  const questionsQuery = useQuery({
    queryKey: ["questions", status],
    queryFn: () => listQuestions(status),
    refetchInterval: 15_000,
  });

  const replyMutation = useMutation({
    mutationFn: (vars: { id: string; reply: string }) => replyToQuestion(vars.id, vars.reply),
    onSuccess: () => {
      notifications.show({ color: "teal", message: "Reply sent." });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
      close();
      setReplyText("");
      setActive(null);
    },
    onError: () => {
      notifications.show({ color: "red", message: "Could not send the reply." });
    },
  });

  const closeMutation = useMutation({
    mutationFn: (id: string) => closeQuestion(id),
    onSuccess: () => {
      notifications.show({ color: "gray", message: "Closed." });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
    onError: () => {
      notifications.show({ color: "red", message: "Could not close." });
    },
  });

  const openReply = (q: Question) => {
    setActive(q);
    setReplyText("");
    open();
  };

  return (
    <Stack>
      <Group justify="space-between" align="center">
        <div>
          <Title order={2}>Inbox</Title>
          <Text c="dimmed" size="sm">
            Questions the AI escalated to you.
          </Text>
        </div>
        <Group>
          <SegmentedControl
            value={filter}
            onChange={(v: string) => setFilter(v as QuestionStatus | "all")}
            data={[
              { label: "Open", value: "submitted" },
              { label: "Resolved", value: "resolved" },
              { label: "Closed", value: "closed" },
              { label: "All", value: "all" },
            ]}
          />
          <Tooltip label="Refresh">
            <ActionIcon
              variant="subtle"
              onClick={() => queryClient.invalidateQueries({ queryKey: ["questions"] })}
              aria-label="Refresh"
            >
              <IconRefresh size={18} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      {questionsQuery.isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {questionsQuery.isError && (
        <Alert color="red" title="Could not load the inbox">
          Try refreshing in a moment.
        </Alert>
      )}

      {questionsQuery.isSuccess && questionsQuery.data.length === 0 && (
        <Card withBorder radius="md" p="xl">
          <Center py="xl">
            <Stack align="center" gap="xs">
              <IconArchive size={32} stroke={1.4} />
              <Text fw={500}>Nothing waiting on you.</Text>
              <Text c="dimmed" size="sm">
                When the AI escalates a question, it'll appear here.
              </Text>
            </Stack>
          </Center>
        </Card>
      )}

      {questionsQuery.isSuccess && questionsQuery.data.length > 0 && (
        <Stack gap="sm">
          {questionsQuery.data.map((q) => (
            <Card key={q.id} withBorder radius="md" p="lg">
              <Group justify="space-between" align="flex-start">
                <Box style={{ flex: 1 }}>
                  <Group gap="xs" mb={6}>
                    <Badge color={STATUS_COLOR[q.status]} variant="light">
                      {q.status}
                    </Badge>
                    <Badge color="gray" variant="default">
                      {CHANNEL_LABEL[q.channel] ?? q.channel}
                    </Badge>
                    {q.contact_id && (
                      <Text size="xs" c="dimmed">
                        Contact: {q.contact_id.slice(0, 8)}…
                      </Text>
                    )}
                    <Text size="xs" c="dimmed" ml="auto">
                      {dayjs(q.created_at).format("MMM D, HH:mm")}
                    </Text>
                  </Group>
                  <Text mb="sm">{q.question_text}</Text>
                  {q.ai_answer_attempt && (
                    <Card withBorder radius="sm" bg="gray.0" p="sm" mb="sm">
                      <Group gap="xs" mb={4}>
                        <IconRobot size={14} />
                        <Text size="xs" fw={600} c="dimmed">
                          AI's attempt
                        </Text>
                      </Group>
                      <Text size="sm" c="dimmed">
                        {q.ai_answer_attempt}
                      </Text>
                    </Card>
                  )}
                  {q.owner_reply && (
                    <Card withBorder radius="sm" bg="teal.0" p="sm">
                      <Text size="xs" fw={600} c="teal.7" mb={4}>
                        Your reply
                      </Text>
                      <Text size="sm">{q.owner_reply}</Text>
                    </Card>
                  )}
                </Box>
                {q.status === "submitted" && (
                  <Stack gap="xs">
                    <Button size="xs" leftSection={<IconSend size={14} />} onClick={() => openReply(q)}>
                      Reply
                    </Button>
                    <Button
                      size="xs"
                      variant="default"
                      onClick={() => {
                        if (globalThis.confirm("Are you sure you want to close this question?")) {
                          closeMutation.mutate(q.id);
                        }
                      }}
                      loading={closeMutation.isPending && closeMutation.variables === q.id}
                    >
                      Close
                    </Button>
                  </Stack>
                )}
              </Group>
            </Card>
          ))}
        </Stack>
      )}

      <Modal opened={opened} onClose={close} title={active ? "Reply to question" : ""} size="lg">
        {active && (
          <Stack>
            <Card withBorder p="sm" bg="gray.0">
              <Text size="sm" fw={500}>
                {active.question_text}
              </Text>
              {active.contact_id && (
                <Text size="xs" c="dimmed" mt={4}>
                  Contact: {active.contact_id.slice(0, 8)}…
                </Text>
              )}
            </Card>
            <ScrollArea.Autosize mah={240}>
              <Textarea
                autosize
                minRows={6}
                placeholder="Type the reply you'd like the AI to relay back to the asker…"
                value={replyText}
                onChange={(e) => setReplyText(e.currentTarget.value)}
              />
            </ScrollArea.Autosize>
            <Group justify="flex-end">
              <Button variant="default" onClick={close}>
                Cancel
              </Button>
              <Button
                onClick={() => active && replyMutation.mutate({ id: active.id, reply: replyText.trim() })}
                loading={replyMutation.isPending}
                disabled={replyText.trim().length === 0}
              >
                Send reply
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
