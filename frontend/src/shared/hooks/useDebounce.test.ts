import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDebounce } from "./useDebounce";

describe("useDebounce", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("returns the initial value immediately", () => {
    const { result } = renderHook(() => useDebounce("a", 200));
    expect(result.current).toBe("a");
  });

  it("updates only after the delay elapses", () => {
    const { result, rerender } = renderHook(({ v }) => useDebounce(v, 200), { initialProps: { v: "a" } });
    rerender({ v: "b" });
    expect(result.current).toBe("a"); // not yet — delay hasn't elapsed
    act(() => vi.advanceTimersByTime(199));
    expect(result.current).toBe("a");
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe("b");
  });

  it("resets the timer on rapid changes (debounces)", () => {
    const { result, rerender } = renderHook(({ v }) => useDebounce(v, 200), { initialProps: { v: "a" } });
    rerender({ v: "b" });
    act(() => vi.advanceTimersByTime(150));
    rerender({ v: "c" }); // before "b" settled — timer restarts
    act(() => vi.advanceTimersByTime(150));
    expect(result.current).toBe("a"); // still "a": neither change has settled
    act(() => vi.advanceTimersByTime(50));
    expect(result.current).toBe("c"); // only the final value lands
  });
});
