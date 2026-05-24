import { Alert, Card, Center, Group, Loader, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { IconChartBar } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../../core/api/client";

interface UsageStats {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_read_tokens: number;
  total_input_cost: string;
  total_cache_read_cost: string;
  total_output_cost: string;
  total_cost: string;
  total_calls: number;
}

async function fetchUsageStats(): Promise<UsageStats> {
  const { data } = await api.get<UsageStats>("/api/v1/llm-usage/stats");
  return data;
}

function formatCost(usd: string): string {
  const n = Number(usd);
  if (Number.isNaN(n)) return "$0.00";
  return n < 0.01 ? `$${n.toFixed(6)}` : `$${n.toFixed(2)}`;
}

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <Card withBorder radius="md" p="lg" h="100%">
      <Text size="xs" tt="uppercase" c="dimmed" fw={600}>
        {label}
      </Text>
      <Text size="xl" fw={700} mt={6}>
        {value}
      </Text>
      {hint && (
        <Text size="xs" c="dimmed" mt={4}>
          {hint}
        </Text>
      )}
    </Card>
  );
}

export function UsagePage() {
  const statsQuery = useQuery({ queryKey: ["usage-stats"], queryFn: fetchUsageStats });

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>Usage &amp; cost</Title>
          <Text c="dimmed" size="sm">
            Per-tenant token + USD ledger. Aggregated server-side.
          </Text>
        </div>
      </Group>

      {statsQuery.isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {statsQuery.isError && <Alert color="red">Could not load usage stats.</Alert>}

      {statsQuery.isSuccess && (
        <Stack>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
            <StatCard label="Total cost" value={formatCost(statsQuery.data.total_cost)} />
            <StatCard
              label="LLM calls"
              value={statsQuery.data.total_calls.toLocaleString()}
              hint="across all conversations"
            />
            <StatCard
              label="Input tokens"
              value={statsQuery.data.total_input_tokens.toLocaleString()}
            />
            <StatCard
              label="Output tokens"
              value={statsQuery.data.total_output_tokens.toLocaleString()}
            />
          </SimpleGrid>

          <Card withBorder p="lg" radius="md">
            <Group gap="xs" mb="sm">
              <IconChartBar size={18} />
              <Text fw={600}>Cost breakdown</Text>
            </Group>
            <Stack gap={6}>
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  Input
                </Text>
                <Text size="sm">{formatCost(statsQuery.data.total_input_cost)}</Text>
              </Group>
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  Cache reads
                </Text>
                <Text size="sm">{formatCost(statsQuery.data.total_cache_read_cost)}</Text>
              </Group>
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  Output
                </Text>
                <Text size="sm">{formatCost(statsQuery.data.total_output_cost)}</Text>
              </Group>
            </Stack>
          </Card>
        </Stack>
      )}
    </Stack>
  );
}
