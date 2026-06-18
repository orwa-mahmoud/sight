import { Anchor, Group, Loader, Paper, Stack, Text } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useAuth } from "@auth/useAuth";
import { api } from "@core/api/client";

interface ProcessingDocument {
  id: string;
  filename: string;
  status: string;
}

const MAX_VISIBLE = 3;
const POLL_MS = 2500;

// Reads in-flight uploads from the backend (not browser state), so a page
// refresh re-derives progress from the DB and the indicator keeps showing.
async function fetchProcessingDocuments(): Promise<ProcessingDocument[]> {
  const { data } = await api.get<ProcessingDocument[]>("/api/v1/documents/processing");
  return data;
}

/**
 * Global, app-level ingestion progress. Mounted once in the shell so it stays
 * visible while the user moves between pages — uploading a document never blocks
 * navigation. It polls only while work is in flight; an idle app makes no extra
 * requests. The shared `["documents"]` query prefix means a new upload on the
 * Documents page invalidates this too, so the indicator appears immediately.
 */
export function IngestionProgress() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const { data } = useQuery({
    queryKey: ["documents", "processing"],
    queryFn: fetchProcessingDocuments,
    enabled: Boolean(user),
    refetchInterval: (query) => ((query.state.data?.length ?? 0) > 0 ? POLL_MS : false),
  });

  const docs = data ?? [];
  if (docs.length === 0) {
    return null;
  }

  const visible = docs.slice(0, MAX_VISIBLE);
  const hidden = docs.length - visible.length;

  return (
    <Paper
      role="status"
      aria-live="polite"
      aria-label={t("ingestion.ariaLabel")}
      shadow="md"
      radius="md"
      withBorder
      p="md"
      style={{
        position: "fixed",
        bottom: "var(--mantine-spacing-lg)",
        insetInlineEnd: "var(--mantine-spacing-lg)",
        zIndex: 200,
        width: 300,
        maxWidth: "calc(100vw - 2 * var(--mantine-spacing-lg))",
      }}
    >
      <Group gap="xs" wrap="nowrap" mb="xs">
        <Loader size="sm" color="coral" />
        <Text size="sm" fw={600}>
          {t("ingestion.processing", { n: docs.length })}
        </Text>
      </Group>
      <Stack gap={4}>
        {visible.map((doc) => (
          <Text key={doc.id} size="xs" c="dimmed" lineClamp={1}>
            {doc.filename}
          </Text>
        ))}
        {hidden > 0 && (
          <Text size="xs" c="dimmed">
            {t("ingestion.andMore", { n: hidden })}
          </Text>
        )}
      </Stack>
      <Anchor component={Link} to="/documents" size="xs" mt="xs" style={{ display: "inline-block" }}>
        {t("ingestion.viewAll")}
      </Anchor>
    </Paper>
  );
}
