import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { TestWrapper } from "../../test/wrapper";
import { UsagePage } from "./UsagePage";

vi.mock("../../core/api/client", () => ({
  api: { get: vi.fn().mockResolvedValue({ data: { total_input_tokens: 0, total_output_tokens: 0, total_cache_read_tokens: 0, total_input_cost: "0", total_cache_read_cost: "0", total_output_cost: "0", total_cost: "0", total_calls: 0 } }), post: vi.fn(), put: vi.fn(), delete: vi.fn(), interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } }, defaults: { headers: {} } },
  getToken: () => "tok", setToken: vi.fn(), clearToken: vi.fn(),
}));

describe("UsagePage", () => {
  it("renders without crash", () => {
    const { container } = render(<UsagePage />, { wrapper: TestWrapper });
    expect(container).toBeTruthy();
  });
});
