import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { TestWrapper } from "../../test/wrapper";
import { SettingsPage } from "./SettingsPage";

vi.mock("../../core/api/client", () => ({
  api: { get: vi.fn().mockResolvedValue({ data: {} }), post: vi.fn(), put: vi.fn(), delete: vi.fn(), interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } }, defaults: { headers: {} } },
  getToken: () => "tok", setToken: vi.fn(), clearToken: vi.fn(),
}));

describe("SettingsPage", () => {
  it("renders without crashing", () => {
    const { container } = render(<SettingsPage />, { wrapper: TestWrapper });
    expect(container).toBeTruthy();
  });
});
