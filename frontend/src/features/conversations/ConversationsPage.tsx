import { Card, Center, Stack, Text, Title } from "@mantine/core";
import { IconMessageCircle } from "@tabler/icons-react";

export function ConversationsPage() {
  return (
    <Stack>
      <div>
        <Title order={2}>Conversations</Title>
        <Text c="dimmed" size="sm">
          Threads between askers and the AI, plus your own admin chats.
        </Text>
      </div>
      <Card withBorder radius="md" p="xl">
        <Center py="xl">
          <Stack align="center" gap="xs" maw={420} ta="center">
            <IconMessageCircle size={32} stroke={1.4} />
            <Text fw={500}>Conversations dashboard — coming with the channels phase.</Text>
            <Text size="sm" c="dimmed">
              Once the WhatsApp and Telegram webhook adapters land, every asker thread will appear
              here with full tool-exchange fidelity (the AI's tool calls, results, and replies
              preserved in their native format).
            </Text>
          </Stack>
        </Center>
      </Card>
    </Stack>
  );
}
