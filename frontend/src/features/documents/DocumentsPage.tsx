import { Badge, Box, Button, FileButton, Group, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  IconAlertCircle,
  IconCircleCheck,
  IconFileText,
  IconMessageCircle,
  IconTrash,
  IconUpload,
} from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { api } from "@core/api/client";
import {
  DataTable,
  SelectFilter,
  useFrontendData,
  type CellProps,
  type ColumnDef,
  type RowAction,
} from "@shared/components/datatable";
import { EmptyState } from "@shared/components/EmptyState";
import { useMutationWithNotification } from "@shared/hooks/useMutationWithNotification";

interface DocumentSummary {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  chunk_count: number;
  error: string | null;
  created_at: string;
  updated_at: string;
}

const STATUS_COLOR: Record<string, string> = {
  ready: "teal",
  ingesting: "blue",
  uploaded: "gray",
  failed: "red",
};
const STATUSES = ["uploaded", "ingesting", "ready", "failed"] as const;

async function listDocuments(): Promise<DocumentSummary[]> {
  const { data } = await api.get<DocumentSummary[]>("/api/v1/documents");
  return data;
}

async function uploadDocument(file: File): Promise<DocumentSummary> {
  const formData = new FormData();
  formData.append("file", file);
  // Clear the instance's default application/json so axios sets
  // `multipart/form-data; boundary=...` itself — a hardcoded multipart header
  // omits the boundary and the server can't parse the body.
  const { data } = await api.post<DocumentSummary>("/api/v1/documents", formData, {
    headers: { "Content-Type": undefined },
    timeout: 120_000,
  });
  return data;
}

async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/api/v1/documents/${id}`);
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const PROCESSING_STATUSES = new Set(["uploaded", "ingesting"]);

// Cell renderers are module-level components (stable identity; keeps them out of
// the page component body per Sonar S6478).
function FileCell({ row }: Readonly<CellProps<DocumentSummary>>) {
  return (
    <Group gap="xs" wrap="nowrap">
      <IconCircleCheck
        size={14}
        color={row.status === "ready" ? "var(--mantine-color-teal-6)" : "var(--mantine-color-gray-4)"}
      />
      <Text size="sm">{row.filename}</Text>
    </Group>
  );
}

function StatusCell({ row }: Readonly<CellProps<DocumentSummary>>) {
  const badge = (
    <Badge color={STATUS_COLOR[row.status] ?? "gray"} variant="light">
      {row.status}
    </Badge>
  );
  if (row.status === "failed" && row.error) {
    return (
      <Group gap={6} wrap="nowrap" align="center">
        <IconAlertCircle size={14} color="var(--mantine-color-red-6)" />
        {badge}
        <Text size="xs" c="red" lineClamp={1} maw={220} title={row.error}>
          {row.error}
        </Text>
      </Group>
    );
  }
  return badge;
}

function ChunkCountCell({ row }: Readonly<CellProps<DocumentSummary>>) {
  return <Text size="sm">{row.chunk_count}</Text>;
}

function SizeCell({ row }: Readonly<CellProps<DocumentSummary>>) {
  return <Text size="sm">{formatBytes(row.size_bytes)}</Text>;
}

function UploadedCell({ row }: Readonly<CellProps<DocumentSummary>>) {
  return (
    <Text size="sm" c="dimmed">
      {dayjs(row.created_at).format("MMM D, HH:mm")}
    </Text>
  );
}

export function DocumentsPage() {
  const { t } = useTranslation();
  // Poll while any document is still processing so it flips to "ready"
  // (or "failed") in the UI without a manual refresh.
  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    refetchInterval: (query) =>
      query.state.data?.some((d) => PROCESSING_STATUSES.has(d.status)) ? 4000 : false,
  });

  const uploadMutation = useMutationWithNotification({
    mutationFn: uploadDocument,
    successMessage: t("documents.uploaded"),
    invalidateKeys: [["documents"]],
    // A failed ingestion is still persisted as a FAILED document — refetch so the
    // owner sees it (with the error reason) right away, not just the toast.
    invalidateOnError: true,
    // Status-aware error: a 413 means the file exceeded the size cap, not a bad type.
    onError: (err) => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      const message = status === 413 ? t("documents.uploadTooLarge") : t("documents.uploadFailed");
      notifications.show({ color: "red", message });
    },
  });

  const deleteMutation = useMutationWithNotification({
    mutationFn: deleteDocument,
    successMessage: t("documents.deleted"),
    errorMessage: t("documents.deleteFailed"),
    invalidateKeys: [["documents"]],
  });

  const columns = useMemo<ColumnDef<DocumentSummary>[]>(
    () => [
      {
        key: "filename",
        header: t("documents.colFile"),
        sortable: true,
        sortValue: (d) => d.filename,
        Cell: FileCell,
      },
      { key: "status", header: t("documents.colStatus"), Cell: StatusCell },
      {
        key: "chunk_count",
        header: t("documents.colChunks"),
        sortable: true,
        sortValue: (d) => d.chunk_count,
        Cell: ChunkCountCell,
      },
      {
        key: "size_bytes",
        header: t("documents.colSize"),
        sortable: true,
        sortValue: (d) => d.size_bytes,
        Cell: SizeCell,
      },
      {
        key: "created_at",
        header: t("documents.colUploaded"),
        sortable: true,
        sortValue: (d) => d.created_at,
        Cell: UploadedCell,
      },
    ],
    [t],
  );

  const rowActions = useMemo<RowAction<DocumentSummary>[]>(
    () => [
      {
        key: "delete",
        label: t("common.delete"),
        color: "red",
        icon: <IconTrash size={16} />,
        onClick: (d) => deleteMutation.mutate(d.id),
        confirm: {
          title: t("documents.confirmDeleteTitle"),
          message: () => t("documents.confirmDelete"),
          confirmLabel: t("common.delete"),
          danger: true,
        },
      },
    ],
    [t, deleteMutation],
  );

  const source = useFrontendData<DocumentSummary>({
    data: documentsQuery.data ?? [],
    columns,
    searchKeys: ["filename"],
    isLoading: documentsQuery.isLoading,
    error: documentsQuery.error,
    refetch: documentsQuery.refetch,
  });

  return (
    <Stack>
      <Group justify="space-between" align="flex-start">
        <Box>
          <Title order={2}>{t("documents.title")}</Title>
          <Text c="dimmed" size="sm">
            {t("documents.subtitle")}
          </Text>
        </Box>
      </Group>

      <DataTable
        source={source}
        columns={columns}
        rowKey={(d) => d.id}
        rowActions={rowActions}
        tableLabel={t("documents.title")}
        searchPlaceholder={t("documents.searchPlaceholder")}
        toolbar={
          <Group gap="sm">
            <Button
              component={Link}
              to="/chat"
              variant="light"
              color="coral"
              leftSection={<IconMessageCircle size={18} />}
            >
              {t("documents.testInChat")}
            </Button>
            <FileButton
              onChange={(file) => file && uploadMutation.mutate(file)}
              accept=".pdf,.md,.markdown,.txt,.docx"
            >
              {(props) => (
                <Button {...props} leftSection={<IconUpload size={18} />} loading={uploadMutation.isPending}>
                  {t("documents.upload")}
                </Button>
              )}
            </FileButton>
          </Group>
        }
        emptyState={
          <EmptyState
            icon={<IconFileText size={32} stroke={1.4} />}
            title={t("documents.emptyTitle")}
            description={t("documents.emptyDesc")}
          />
        }
        filters={
          <SelectFilter
            source={source}
            filterKey="status"
            label={t("documents.filterStatus")}
            data={STATUSES.map((s) => ({ value: s, label: s }))}
          />
        }
        filterLabels={{ status: (v) => `${t("documents.filterStatus")}: ${String(v)}` }}
      />
    </Stack>
  );
}
