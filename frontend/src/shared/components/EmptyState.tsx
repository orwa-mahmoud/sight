import { Card, Center, Stack, Text } from "@mantine/core";
import type { ReactNode } from "react";

export interface EmptyStateProps {
  readonly icon?: ReactNode;
  readonly title: string;
  readonly description?: string;
  readonly action?: ReactNode;
}

/** Standard "no data" panel: icon + title + guidance + optional action. */
export function EmptyState({ icon, title, description, action }: Readonly<EmptyStateProps>) {
  return (
    <Card withBorder radius="md" p="xl">
      <Center py="xl">
        <Stack align="center" gap="xs">
          {icon}
          <Text fw={500}>{title}</Text>
          {description ? (
            <Text c="dimmed" size="sm" ta="center" maw={420}>
              {description}
            </Text>
          ) : null}
          {action}
        </Stack>
      </Center>
    </Card>
  );
}
