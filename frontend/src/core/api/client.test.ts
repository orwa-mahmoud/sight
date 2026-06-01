import { describe, it, expect, vi } from "vitest";
import { AxiosError, type AxiosResponse } from "axios";
import { api, setUnauthorizedHandler } from "./client";

describe("api instance", () => {
  it("has correct timeout", () => {
    expect(api.defaults.timeout).toBe(30_000);
  });

  it("has JSON content type", () => {
    expect(api.defaults.headers["Content-Type"]).toBe("application/json");
  });

  it("sends credentials so the auth cookie travels with every request", () => {
    expect(api.defaults.withCredentials).toBe(true);
  });

  it("defaults to a same-origin (relative) base URL when VITE_API_URL is unset", async () => {
    vi.stubEnv("VITE_API_URL", undefined);
    vi.resetModules();
    const { api: freshApi } = await import("./client");
    expect(freshApi.defaults.baseURL).toBe("");
    vi.unstubAllEnvs();
  });
});

describe("response interceptor", () => {
  it("invokes the unauthorized handler on a 401 response", async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    api.defaults.adapter = async (config) => {
      throw new AxiosError("401", "ERR_BAD_REQUEST", config, null, {
        status: 401, data: {}, headers: {}, statusText: "Unauthorized", config,
      } as AxiosResponse);
    };
    await api.get("/protected").catch(() => {});
    expect(onUnauthorized).toHaveBeenCalledOnce();
    setUnauthorizedHandler(null);
  });

  it("does not invoke the unauthorized handler on a non-401 error", async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    api.defaults.adapter = async (config) => {
      throw new AxiosError("500", "ERR_BAD_RESPONSE", config, null, {
        status: 500, data: {}, headers: {}, statusText: "Error", config,
      } as AxiosResponse);
    };
    await api.get("/error").catch(() => {});
    expect(onUnauthorized).not.toHaveBeenCalled();
    setUnauthorizedHandler(null);
  });

  it("passes successful responses through", async () => {
    api.defaults.adapter = async (config) =>
      ({ data: { ok: true }, status: 200, statusText: "OK", headers: {}, config }) as AxiosResponse;
    const res = await api.get("/ok");
    expect(res.data).toEqual({ ok: true });
  });
});

describe("BASE_URL configuration", () => {
  it("uses VITE_API_URL env var when set", async () => {
    vi.stubEnv("VITE_API_URL", "https://api.example.com");
    vi.resetModules();
    const { api: freshApi } = await import("./client");
    expect(freshApi.defaults.baseURL).toBe("https://api.example.com");
    vi.unstubAllEnvs();
  });
});
