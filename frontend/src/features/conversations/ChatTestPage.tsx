import {
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Popover,
  ScrollArea,
  Stack,
  Text,
  Textarea,
  Title,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconFileText, IconInfoCircle, IconRefresh, IconSend } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { api } from "@core/api/client";
import { elapsedMsSince, monotonicNow } from "@shared/utils/clock";

interface ChatSource {
  document_id: string;
  snippet: string;
  score: number;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  escalated?: boolean;
  latencyMs?: number;
  totalTokens?: number;
}

interface ChatApiResponse {
  response: string;
  thread_id: string;
  escalated: boolean;
  request_id: string;
  sources?: ChatSource[];
  input_tokens?: number;
  output_tokens?: number;
}

interface DocumentLite {
  id: string;
  filename: string;
  status: string;
}

const PROCESSING_STATUSES = new Set(["uploaded", "ingesting"]);

interface BotConfigLite {
  bot_name: string;
  bot_welcome_message: string;
}

async function listDocuments(): Promise<DocumentLite[]> {
  const { data } = await api.get<DocumentLite[]>("/api/v1/documents");
  return data;
}

async function getBotConfig(): Promise<BotConfigLite> {
  const { data } = await api.get<BotConfigLite>("/api/v1/settings");
  return { bot_name: data.bot_name, bot_welcome_message: data.bot_welcome_message };
}

export function ChatTestPage() {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);

  // The bot's configured greeting, previewed in the empty state so the owner
  // sees exactly how their bot opens a conversation.
  const botConfigQuery = useQuery({ queryKey: ["bot-config"], queryFn: getBotConfig });
  const welcomeMessage = botConfigQuery.data?.bot_welcome_message?.trim();

  // Map document_id → filename so retrieved sources show the real file name.
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const documentName = useMemo(() => {
    const map = new Map<string, string>();
    for (const d of documentsQuery.data ?? []) map.set(d.id, d.filename);
    return (id: string) => map.get(id) ?? `${id.slice(0, 8)}…`;
  }, [documentsQuery.data]);

  // Auto-scroll to the latest message.
  useEffect(() => {
    viewportRef.current?.scrollTo?.({ top: viewportRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const send = async (textArg?: string) => {
    const text = (textArg ?? input).trim();
    if (!text || sending) return;
    setInput("");
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: text }]);
    setSending(true);

    try {
      const payload: Record<string, string> = { message: text };
      if (threadId) payload.thread_id = threadId;
      const startedAt = monotonicNow();
      const { data } = await api.post<ChatApiResponse>("/api/v1/chat", payload);
      const latencyMs = elapsedMsSince(startedAt);
      if (data.thread_id && !threadId) {
        setThreadId(data.thread_id);
      }
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.response,
          sources: data.sources,
          escalated: data.escalated,
          latencyMs,
          totalTokens: (data.input_tokens ?? 0) + (data.output_tokens ?? 0),
        },
      ]);
      if (data.escalated) {
        notifications.show({ color: "orange", message: t("chat.escalated") });
      }
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      const message = status === 429 ? t("chat.rateLimited") : t("chat.error");
      notifications.show({ color: "red", message });
    } finally {
      setSending(false);
    }
  };

  const resetConversation = () => {
    setMessages([]);
    setThreadId(null);
    setInput("");
  };

  const suggestions = [t("chat.suggest1"), t("chat.suggest2"), t("chat.suggest3")];
  const docs = documentsQuery.data ?? [];
  const hasNoDocuments = documentsQuery.isSuccess && docs.length === 0;
  const processingCount = docs.filter((d) => PROCESSING_STATUSES.has(d.status)).length;

  return (
    <Stack>
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>{t("chat.title")}</Title>
          <Text c="dimmed" size="sm">
            {t("chat.subtitle")}
          </Text>
        </div>
        {messages.length > 0 && (
          <Tooltip label={t("chat.reset")}>
            <ActionIcon
              variant="subtle"
              color="gray"
              onClick={resetConversation}
              aria-label={t("chat.reset")}
            >
              <IconRefresh size={18} />
            </ActionIcon>
          </Tooltip>
        )}
      </Group>

      {hasNoDocuments && (
        <Alert variant="light" color="blue" icon={<IconInfoCircle size={18} />} title={t("chat.noDocsTitle")}>
          {t("chat.noDocsBody")}{" "}
          <Anchor component={Link} to="/documents" fw={600}>
            {t("chat.noDocsCta")}
          </Anchor>
        </Alert>
      )}

      {processingCount > 0 && (
        <Alert variant="light" color="yellow" icon={<IconInfoCircle size={18} />}>
          {t("chat.docsProcessing", { n: processingCount })}
        </Alert>
      )}

      <Card withBorder radius="md" p={0} style={{ height: "60vh", display: "flex", flexDirection: "column" }}>
        <ScrollArea style={{ flex: 1 }} p="md" viewportRef={viewportRef}>
          <Stack gap="sm" role="log" aria-live="polite">
            {messages.length === 0 && welcomeMessage && (
              <Card withBorder radius="md" p="sm" bg="coral.0" mr="auto" maw="80%">
                <Text size="xs" fw={600} c="coral.7" mb={4}>
                  {botConfigQuery.data?.bot_name?.trim() || t("chat.ai")}
                </Text>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {welcomeMessage}
                </Text>
              </Card>
            )}
            {messages.length === 0 && (
              <Stack align="center" gap="md" py="xl">
                <Text c="dimmed" ta="center">
                  {t("chat.empty")}
                </Text>
                <Stack gap={6} align="center">
                  <Text size="xs" c="dimmed" fw={600} tt="uppercase">
                    {t("chat.suggestionsLabel")}
                  </Text>
                  <Group justify="center" gap="xs">
                    {suggestions.map((s) => (
                      <Button
                        key={s}
                        size="xs"
                        variant="light"
                        color="coral"
                        onClick={() => {
                          send(s);
                        }}
                      >
                        {s}
                      </Button>
                    ))}
                  </Group>
                </Stack>
              </Stack>
            )}
            {messages.map((m) => (
              <Card
                key={m.id}
                withBorder
                radius="md"
                p="sm"
                bg={m.role === "user" ? "gray.0" : "coral.0"}
                ml={m.role === "user" ? "auto" : 0}
                mr={m.role === "assistant" ? "auto" : 0}
                maw="80%"
              >
                <Group gap="xs" mb={4}>
                  <Text size="xs" fw={600} c={m.role === "user" ? "dimmed" : "coral.7"}>
                    {m.role === "user" ? t("chat.you") : t("chat.ai")}
                  </Text>
                  {m.escalated && (
                    <Badge size="xs" color="orange" variant="light">
                      {t("chat.escalatedBadge")}
                    </Badge>
                  )}
                  {m.role === "assistant" && m.latencyMs !== undefined && (
                    <Text size="xs" c="dimmed" ml="auto">
                      {(m.latencyMs / 1000).toFixed(m.latencyMs < 1000 ? 2 : 1)}
                      {t("chat.secondsSuffix")}
                      {m.totalTokens ? ` · ${t("chat.tokens", { n: m.totalTokens })}` : ""}
                    </Text>
                  )}
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {m.content}
                </Text>
                {m.escalated && (
                  <Anchor
                    component={Link}
                    to="/inbox"
                    size="xs"
                    fw={600}
                    c="orange"
                    mt={4}
                    display="inline-block"
                  >
                    {t("chat.viewInInbox")}
                  </Anchor>
                )}
                {m.sources && m.sources.length > 0 && (
                  <Group gap={6} mt="xs" wrap="wrap">
                    <Text size="xs" c="dimmed" fw={600}>
                      {t("chat.sources")}:
                    </Text>
                    {m.sources.map((s) => (
                      <Popover key={s.document_id} width={320} position="top" withArrow shadow="md">
                        <Popover.Target>
                          <Badge
                            size="sm"
                            variant="outline"
                            color="gray"
                            component="button"
                            type="button"
                            leftSection={<IconFileText size={12} />}
                            style={{ cursor: "pointer", textTransform: "none" }}
                          >
                            {documentName(s.document_id)}
                          </Badge>
                        </Popover.Target>
                        <Popover.Dropdown>
                          <Text size="xs" style={{ whiteSpace: "pre-wrap" }}>
                            {s.snippet}
                          </Text>
                        </Popover.Dropdown>
                      </Popover>
                    ))}
                  </Group>
                )}
              </Card>
            ))}
            {sending && (
              <Card withBorder radius="md" p="sm" bg="coral.0" mr="auto" maw="80%">
                <Group gap="xs">
                  <Loader size="xs" color="coral" />
                  <Text size="sm" c="dimmed">
                    {t("chat.thinking")}
                  </Text>
                </Group>
              </Card>
            )}
          </Stack>
        </ScrollArea>
        <Group p="md" style={{ borderTop: "1px solid var(--mantine-color-gray-3)" }}>
          <Textarea
            style={{ flex: 1 }}
            placeholder={t("chat.placeholder")}
            autosize
            minRows={1}
            maxRows={4}
            value={input}
            onChange={(e) => setInput(e.currentTarget.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <Button
            onClick={() => {
              send();
            }}
            loading={sending}
            disabled={sending}
            aria-label={t("chat.sendAria")}
            leftSection={<IconSend size={16} />}
          >
            {t("chat.send")}
          </Button>
        </Group>
      </Card>
    </Stack>
  );
}
