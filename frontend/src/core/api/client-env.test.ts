import { describe, it, expect, vi } from "vitest";

describe("client with VITE_API_URL", () => {
  it("uses env var for base URL", async () => {
    vi.stubEnv("VITE_API_URL", "https://api.prod.com");
    vi.resetModules();
    const { api } = await import("./client");
    expect(api.defaults.baseURL).toBe("https://api.prod.com");
    vi.unstubAllEnvs();
  });
});
