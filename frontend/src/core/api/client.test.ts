import { describe, it, expect, beforeEach, vi } from "vitest";
import { AxiosError, type AxiosResponse } from "axios";
import { api, getToken, setToken, clearToken } from "./client";

describe("token management", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when no token set", () => {
    expect(getToken()).toBeNull();
  });

  it("stores and retrieves a token", () => {
    setToken("abc");
    expect(getToken()).toBe("abc");
  });

  it("clears the token", () => {
    setToken("abc");
    clearToken();
    expect(getToken()).toBeNull();
  });
});

describe("api instance", () => {
  it("has correct timeout", () => {
    expect(api.defaults.timeout).toBe(30_000);
  });

  it("has JSON content type", () => {
    expect(api.defaults.headers["Content-Type"]).toBe("application/json");
  });
});

describe("request interceptor", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("attaches Bearer token when token exists", async () => {
    setToken("jwt-123");
    let capturedAuth: string | undefined;
    api.defaults.adapter = async (config) => {
      capturedAuth = config.headers?.Authorization as string | undefined;
      return { data: {}, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
    };
    await api.get("/test");
    expect(capturedAuth).toBe("Bearer jwt-123");
  });

  it("omits Authorization header when no token", async () => {
    let capturedAuth: string | undefined;
    api.defaults.adapter = async (config) => {
      capturedAuth = config.headers?.Authorization as string | undefined;
      return { data: {}, status: 200, statusText: "OK", headers: {}, config } as AxiosResponse;
    };
    await api.get("/test");
    expect(capturedAuth).toBeUndefined();
  });
});

describe("response interceptor", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("clears token on 401 response", async () => {
    setToken("will-be-cleared");
    api.defaults.adapter = async (config) => {
      throw new AxiosError("401", "ERR_BAD_REQUEST", config, null, {
        status: 401, data: {}, headers: {}, statusText: "Unauthorized", config,
      } as AxiosResponse);
    };
    await api.get("/protected").catch(() => {});
    expect(getToken()).toBeNull();
  });

  it("keeps token on non-401 error", async () => {
    setToken("stays");
    api.defaults.adapter = async (config) => {
      throw new AxiosError("500", "ERR_BAD_RESPONSE", config, null, {
        status: 500, data: {}, headers: {}, statusText: "Error", config,
      } as AxiosResponse);
    };
    await api.get("/error").catch(() => {});
    expect(getToken()).toBe("stays");
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
