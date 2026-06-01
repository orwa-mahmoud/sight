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
import { useTranslation } from "react-i18next";

import { openConfirm } from "@shared/utils/confirm";

import { closeQuestion, listQuestions, replyToQuestion } from "./api";
import type { Question, QuestionStatus } from "./types";

const STATUS_COLOR: Record<QuestionStatus, string> = {
  submitted: "coral",
  resolved: "teal",
  closed: "gray",
};

export function InboxPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<QuestionStatus | "all">("submitted");
  const [active, setActive] = useState<Question | null>(null);
  const [replyText, setReplyText] = useState("");
  const [opened, { open, close }] = useDisclosure(false);

  const channelLabel = (channel: string) => t(`channels.${channel}`, { defaultValue: channel });

  const status = filter === "all" ? undefined : filter;
  const questionsQuery = useQuery({
    queryKey: ["questions", status],
    queryFn: () => listQuestions(status),
    refetchInterval: 15_000,
  });

  const replyMutation = useMutation({
    mutationFn: (vars: { id: string; reply: string }) => replyToQuestion(vars.id, vars.reply),
    onSuccess: () => {
      notifications.show({ color: "teal", message: t("inbox.replySent") });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
      close();
      setReplyText("");
      setActive(null);
    },
    onError: () => {
      notifications.show({ color: "red", message: t("inbox.replyError") });
    },
  });

  const closeMutation = useMutation({
    mutationFn: (id: string) => closeQuestion(id),
    onSuccess: () => {
      notifications.show({ color: "gray", message: t("inbox.closed") });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
    onError: () => {
      notifications.show({ color: "red", message: t("inbox.closeError") });
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
          <Title order={2}>{t("inbox.title")}</Title>
          <Text c="dimmed" size="sm">
            {t("inbox.subtitle")}
          </Text>
        </div>
        <Group>
          <SegmentedControl
            value={filter}
            onChange={(v: string) => setFilter(v as QuestionStatus | "all")}
            data={[
              { label: t("inbox.filterOpen"), value: "submitted" },
              { label: t("inbox.filterResolved"), value: "resolved" },
              { label: t("inbox.filterClosed"), value: "closed" },
              { label: t("inbox.filterAll"), value: "all" },
            ]}
          />
          <Tooltip label={t("inbox.refresh")}>
            <ActionIcon
              variant="subtle"
              onClick={() => queryClient.invalidateQueries({ queryKey: ["questions"] })}
              aria-label={t("inbox.refresh")}
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
        <Alert color="red" title={t("inbox.loadError")}>
          {t("inbox.loadErrorHint")}
        </Alert>
      )}

      {questionsQuery.isSuccess && questionsQuery.data.length === 0 && (
        <Card withBorder radius="md" p="xl">
          <Center py="xl">
            <Stack align="center" gap="xs">
              <IconArchive size={32} stroke={1.4} />
              <Text fw={500}>{t("inbox.emptyTitle")}</Text>
              <Text c="dimmed" size="sm">
                {t("inbox.emptyDesc")}
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
                      {channelLabel(q.channel)}
                    </Badge>
                    {q.contact_id && (
                      <Text size="xs" c="dimmed">
                        {t("inbox.contact")} {q.contact_id.slice(0, 8)}…
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
                          {t("inbox.aiAttempt")}
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
                        {t("inbox.yourReply")}
                      </Text>
                      <Text size="sm">{q.owner_reply}</Text>
                    </Card>
                  )}
                </Box>
                {q.status === "submitted" && (
                  <Stack gap="xs">
                    <Button size="xs" leftSection={<IconSend size={14} />} onClick={() => openReply(q)}>
                      {t("inbox.reply")}
                    </Button>
                    <Button
                      size="xs"
                      variant="default"
                      onClick={() =>
                        openConfirm({
                          title: t("inbox.confirmCloseTitle"),
                          message: t("inbox.confirmClose"),
                          confirmLabel: t("inbox.close"),
                          cancelLabel: t("common.cancel"),
                          danger: true,
                          onConfirm: () => closeMutation.mutate(q.id),
                        })
                      }
                      loading={closeMutation.isPending && closeMutation.variables === q.id}
                    >
                      {t("inbox.close")}
                    </Button>
                  </Stack>
                )}
              </Group>
            </Card>
          ))}
        </Stack>
      )}

      <Modal opened={opened} onClose={close} title={active ? t("inbox.replyModalTitle") : ""} size="lg">
        {active && (
          <Stack>
            <Card withBorder p="sm" bg="gray.0">
              <Text size="sm" fw={500}>
                {active.question_text}
              </Text>
              {active.contact_id && (
                <Text size="xs" c="dimmed" mt={4}>
                  {t("inbox.contact")} {active.contact_id.slice(0, 8)}…
                </Text>
              )}
            </Card>
            <ScrollArea.Autosize mah={240}>
              <Textarea
                autosize
                minRows={6}
                placeholder={t("inbox.replyPlaceholder")}
                value={replyText}
                onChange={(e) => setReplyText(e.currentTarget.value)}
              />
            </ScrollArea.Autosize>
            <Group justify="flex-end">
              <Button variant="default" onClick={close}>
                {t("common.cancel")}
              </Button>
              <Button
                onClick={() => active && replyMutation.mutate({ id: active.id, reply: replyText.trim() })}
                loading={replyMutation.isPending}
                disabled={replyText.trim().length === 0}
              >
                {t("inbox.sendReply")}
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
