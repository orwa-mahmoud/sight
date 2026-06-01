import { Text } from "@mantine/core";
import { modals } from "@mantine/modals";

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
}

/** Open a confirmation modal; runs `onConfirm` only if the user confirms. */
export function openConfirm({
  title,
  message,
  confirmLabel,
  cancelLabel = "Cancel",
  danger,
  onConfirm,
}: ConfirmOptions): void {
  modals.openConfirmModal({
    title,
    children: <Text size="sm">{message}</Text>,
    labels: { confirm: confirmLabel, cancel: cancelLabel },
    confirmProps: danger ? { color: "red" } : undefined,
    onConfirm,
  });
}
