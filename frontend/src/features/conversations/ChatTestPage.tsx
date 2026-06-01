import { Button, Card, Group, ScrollArea, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconSend } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@core/api/client";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatApiResponse {
  response: string;
  thread_id: string;
  escalated: boolean;
  request_id: string;
}

export function ChatTestPage() {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);

  const send = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: text }]);
    setSending(true);

    try {
      const payload: Record<string, string> = { message: text };
      if (threadId) payload.thread_id = threadId;
      const { data } = await api.post<ChatApiResponse>("/api/v1/chat", payload);
      if (data.thread_id && !threadId) {
        setThreadId(data.thread_id);
      }
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: data.response },
      ]);
      if (data.escalated) {
        notifications.show({ color: "orange", message: t("chat.escalated") });
      }
    } catch {
      notifications.show({ color: "red", message: t("chat.error") });
    } finally {
      setSending(false);
    }
  };

  return (
    <Stack>
      <div>
        <Title order={2}>{t("chat.title")}</Title>
        <Text c="dimmed" size="sm">
          {t("chat.subtitle")}
        </Text>
      </div>

      <Card withBorder radius="md" p={0} style={{ height: "60vh", display: "flex", flexDirection: "column" }}>
        <ScrollArea style={{ flex: 1 }} p="md">
          <Stack gap="sm" role="log" aria-live="polite">
            {messages.length === 0 && (
              <Text c="dimmed" ta="center" py="xl">
                {t("chat.empty")}
              </Text>
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
                <Text size="xs" fw={600} c={m.role === "user" ? "dimmed" : "coral.7"} mb={4}>
                  {m.role === "user" ? t("chat.you") : t("chat.ai")}
                </Text>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {m.content}
                </Text>
              </Card>
            ))}
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
                void send();
              }
            }}
          />
          <Button
            onClick={() => void send()}
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
