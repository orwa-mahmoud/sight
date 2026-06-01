import { notifications } from "@mantine/notifications";
import {
  useMutation,
  useQueryClient,
  type QueryKey,
  type UseMutationOptions,
  type UseMutationResult,
} from "@tanstack/react-query";

export interface MutationNotificationOptions<TData, TError, TVariables>
  extends Omit<UseMutationOptions<TData, TError, TVariables>, "onSuccess" | "onError"> {
  /** Shown (teal) on success. */
  successMessage?: string;
  /** Shown (red) on error. */
  errorMessage?: string;
  /** Query keys to invalidate on success. */
  invalidateKeys?: QueryKey[];
  onSuccess?: (data: TData, variables: TVariables) => void;
  onError?: (error: TError, variables: TVariables) => void;
}

/**
 * `useMutation` wrapper that shows success/error notifications and invalidates
 * queries — removes the repeated onSuccess/onError boilerplate across pages.
 */
export function useMutationWithNotification<TData = unknown, TError = Error, TVariables = void>(
  options: MutationNotificationOptions<TData, TError, TVariables>,
): UseMutationResult<TData, TError, TVariables> {
  const queryClient = useQueryClient();
  const { successMessage, errorMessage, invalidateKeys, onSuccess, onError, ...rest } = options;

  return useMutation<TData, TError, TVariables>({
    ...rest,
    onSuccess: (data, variables) => {
      if (successMessage) notifications.show({ color: "teal", message: successMessage });
      if (invalidateKeys) {
        for (const queryKey of invalidateKeys) void queryClient.invalidateQueries({ queryKey });
      }
      onSuccess?.(data, variables);
    },
    onError: (error, variables) => {
      if (errorMessage) notifications.show({ color: "red", message: errorMessage });
      onError?.(error, variables);
    },
  });
}
