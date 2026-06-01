import { Badge, Box, Button, FileButton, Group, Stack, Text, Title } from "@mantine/core";
import { IconCircleCheck, IconFileText, IconTrash, IconUpload } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@core/api/client";
import {
  DataTable,
  SelectFilter,
  useFrontendData,
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
  const { data } = await api.post<DocumentSummary>("/api/v1/documents", formData, {
    headers: { "Content-Type": "multipart/form-data" },
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

export function DocumentsPage() {
  const { t } = useTranslation();
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });

  const uploadMutation = useMutationWithNotification({
    mutationFn: uploadDocument,
    successMessage: t("documents.uploaded"),
    errorMessage: t("documents.uploadFailed"),
    invalidateKeys: [["documents"]],
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
        accessor: (d) => (
          <Group gap="xs" wrap="nowrap">
            <IconCircleCheck
              size={14}
              color={d.status === "ready" ? "var(--mantine-color-teal-6)" : "var(--mantine-color-gray-4)"}
            />
            <Text size="sm">{d.filename}</Text>
          </Group>
        ),
      },
      {
        key: "status",
        header: t("documents.colStatus"),
        accessor: (d) => (
          <Badge color={STATUS_COLOR[d.status] ?? "gray"} variant="light">
            {d.status}
          </Badge>
        ),
      },
      {
        key: "chunk_count",
        header: t("documents.colChunks"),
        sortable: true,
        sortValue: (d) => d.chunk_count,
        accessor: (d) => <Text size="sm">{d.chunk_count}</Text>,
      },
      {
        key: "size_bytes",
        header: t("documents.colSize"),
        sortable: true,
        sortValue: (d) => d.size_bytes,
        accessor: (d) => <Text size="sm">{formatBytes(d.size_bytes)}</Text>,
      },
      {
        key: "created_at",
        header: t("documents.colUploaded"),
        sortable: true,
        sortValue: (d) => d.created_at,
        accessor: (d) => (
          <Text size="sm" c="dimmed">
            {dayjs(d.created_at).format("MMM D, HH:mm")}
          </Text>
        ),
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
