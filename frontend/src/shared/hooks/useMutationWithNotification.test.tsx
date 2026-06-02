import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

import { notifications } from "@mantine/notifications";

import { useMutationWithNotification } from "./useMutationWithNotification";

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  const invalidateSpy = vi.spyOn(qc, "invalidateQueries").mockResolvedValue(undefined);
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return { Wrapper, invalidateSpy };
}

describe("useMutationWithNotification", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows a success toast and invalidates keys on success", async () => {
    const { Wrapper, invalidateSpy } = makeWrapper();
    const { result } = renderHook(
      () =>
        useMutationWithNotification({
          mutationFn: async (x: number) => x * 2,
          successMessage: "ok",
          invalidateKeys: [["a"]],
        }),
      { wrapper: Wrapper },
    );
    await act(async () => {
      await result.current.mutateAsync(2);
    });
    expect(notifications.show).toHaveBeenCalledWith(expect.objectContaining({ color: "teal", message: "ok" }));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["a"] });
  });

  it("shows an error toast and does NOT invalidate on error by default", async () => {
    const { Wrapper, invalidateSpy } = makeWrapper();
    const { result } = renderHook(
      () =>
        useMutationWithNotification({
          mutationFn: async () => {
            throw new Error("boom");
          },
          errorMessage: "failed",
          invalidateKeys: [["a"]],
        }),
      { wrapper: Wrapper },
    );
    await act(async () => {
      await result.current.mutateAsync().catch(() => undefined);
    });
    expect(notifications.show).toHaveBeenCalledWith(expect.objectContaining({ color: "red", message: "failed" }));
    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it("invalidates on error when invalidateOnError is set", async () => {
    const { Wrapper, invalidateSpy } = makeWrapper();
    const { result } = renderHook(
      () =>
        useMutationWithNotification({
          mutationFn: async () => {
            throw new Error("boom");
          },
          invalidateKeys: [["docs"]],
          invalidateOnError: true,
        }),
      { wrapper: Wrapper },
    );
    await act(async () => {
      await result.current.mutateAsync().catch(() => undefined);
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["docs"] });
  });

  it("forwards custom onSuccess/onError callbacks", async () => {
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const { Wrapper } = makeWrapper();
    const { result } = renderHook(
      () => useMutationWithNotification({ mutationFn: async (x: number) => x, onSuccess, onError }),
      { wrapper: Wrapper },
    );
    await act(async () => {
      await result.current.mutateAsync(5);
    });
    expect(onSuccess).toHaveBeenCalledWith(5, 5);
    expect(onError).not.toHaveBeenCalled();
  });
});
