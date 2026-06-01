import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Center,
  FileButton,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCircleCheck, IconFileText, IconUpload } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";

import { api } from "@core/api/client";

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

const STATUS_COLOR: Record<string, string> = {
  ready: "teal",
  ingesting: "blue",
  uploaded: "gray",
  failed: "red",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      notifications.show({ color: "teal", message: "Document ingested." });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: () => {
      notifications.show({
        color: "red",
        message: "Upload failed. Check file type (PDF, DOCX, Markdown, plain text).",
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      notifications.show({ title: "Deleted", message: "Document removed.", color: "teal" });
    },
    onError: () => {
      notifications.show({ title: "Error", message: "Failed to delete document.", color: "red" });
    },
  });

  return (
    <Stack>
      <Group justify="space-between" align="flex-start">
        <Box>
          <Title order={2}>Knowledge base</Title>
          <Text c="dimmed" size="sm">
            Upload PDFs, Markdown, or DOCX. The AI grounds its answers in these documents using
            hybrid (vector + BM25) retrieval over pgvector.
          </Text>
        </Box>
        <FileButton
          onChange={(file) => file && uploadMutation.mutate(file)}
          accept=".pdf,.md,.markdown,.txt,.docx"
        >
          {(props) => (
            <Button
              {...props}
              leftSection={<IconUpload size={18} />}
              loading={uploadMutation.isPending}
            >
              Upload file
            </Button>
          )}
        </FileButton>
      </Group>

      {documentsQuery.isLoading && (
        <Center py="xl">
          <Loader />
        </Center>
      )}

      {documentsQuery.isError && (
        <Alert color="red" title="Could not load documents">
          Try refreshing.
        </Alert>
      )}

      {documentsQuery.isSuccess && documentsQuery.data.length === 0 && (
        <Card withBorder radius="md" p="xl">
          <Center py="xl">
            <Stack align="center" gap="xs">
              <IconFileText size={32} stroke={1.4} />
              <Text fw={500}>No documents yet.</Text>
              <Text c="dimmed" size="sm">
                Upload a file to get started — chunks are embedded with text-embedding-3-large.
              </Text>
            </Stack>
          </Center>
        </Card>
      )}

      {documentsQuery.isSuccess && documentsQuery.data.length > 0 && (
        <Card withBorder radius="md" p={0}>
          <Table verticalSpacing="sm" horizontalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>File</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Chunks</Table.Th>
                <Table.Th>Size</Table.Th>
                <Table.Th>Uploaded</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {documentsQuery.data.map((d) => (
                <Table.Tr key={d.id}>
                  <Table.Td>
                    <Group gap="xs">
                      <IconCircleCheck
                        size={14}
                        color={
                          d.status === "ready"
                            ? "var(--mantine-color-teal-6)"
                            : "var(--mantine-color-gray-4)"
                        }
                      />
                      <Text size="sm">{d.filename}</Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={STATUS_COLOR[d.status] ?? "gray"} variant="light">
                      {d.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{d.chunk_count}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{formatBytes(d.size_bytes)}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" c="dimmed">
                      {dayjs(d.created_at).format("MMM D, HH:mm")}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Button
                      variant="subtle"
                      color="red"
                      size="xs"
                      onClick={() => {
                        if (globalThis.confirm("Are you sure you want to delete this document?")) {
                          deleteMutation.mutate(d.id);
                        }
                      }}
                      loading={deleteMutation.isPending && deleteMutation.variables === d.id}
                    >
                      Delete
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
}
