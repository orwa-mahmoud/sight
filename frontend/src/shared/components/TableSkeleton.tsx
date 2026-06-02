import { Card, Skeleton, Stack } from "@mantine/core";

/** Loading placeholder for tables/lists — calmer than a bare spinner. */
export function TableSkeleton({ rows = 6 }: Readonly<{ rows?: number }>) {
  return (
    <Card withBorder radius="md" p="md">
      <Stack gap="sm">
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} height={28} radius="sm" />
        ))}
      </Stack>
    </Card>
  );
}
