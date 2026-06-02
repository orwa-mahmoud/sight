import { Alert, Card, Center, Group, Loader, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { IconChartBar } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api } from "@core/api/client";

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

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function StatCard({
  label,
  value,
  hint,
}: Readonly<{ label: string; value: string | number; hint?: string }>) {
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
  const { t } = useTranslation();
  const statsQuery = useQuery({ queryKey: ["usage-stats"], queryFn: fetchUsageStats });

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>{t("usage.title")}</Title>
          <Text c="dimmed" size="sm">
            {t("usage.subtitle")}
          </Text>
        </div>
      </Group>

      {statsQuery.isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}
      {statsQuery.isError && <Alert color="red">{t("usage.loadError")}</Alert>}

      {statsQuery.isSuccess && (
        <Stack>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
            <StatCard label={t("usage.totalCost")} value={formatCost(statsQuery.data.total_cost)} />
            <StatCard
              label={t("usage.llmCalls")}
              value={statsQuery.data.total_calls.toLocaleString()}
              hint={t("usage.acrossConversations")}
            />
            <StatCard
              label={t("usage.inputTokens")}
              value={formatTokens(statsQuery.data.total_input_tokens)}
            />
            <StatCard
              label={t("usage.outputTokens")}
              value={formatTokens(statsQuery.data.total_output_tokens)}
            />
          </SimpleGrid>

          <Card withBorder p="lg" radius="md">
            <Group gap="xs" mb="sm">
              <IconChartBar size={18} />
              <Text fw={600}>{t("usage.costBreakdown")}</Text>
            </Group>
            <Stack gap={6}>
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  {t("usage.input")}
                </Text>
                <Text size="sm">{formatCost(statsQuery.data.total_input_cost)}</Text>
              </Group>
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  {t("usage.cacheReads")}
                </Text>
                <Text size="sm">{formatCost(statsQuery.data.total_cache_read_cost)}</Text>
              </Group>
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  {t("usage.output")}
                </Text>
                <Text size="sm">{formatCost(statsQuery.data.total_output_cost)}</Text>
              </Group>
              {statsQuery.data.total_cache_read_tokens > 0 && (
                <Group justify="space-between" mt="xs">
                  <Text size="sm" c="dimmed">
                    {t("usage.cacheHitTokens")}
                  </Text>
                  <Text size="sm" fw={500} c="teal">
                    {formatTokens(statsQuery.data.total_cache_read_tokens)}
                  </Text>
                </Group>
              )}
            </Stack>
          </Card>
        </Stack>
      )}
    </Stack>
  );
}
