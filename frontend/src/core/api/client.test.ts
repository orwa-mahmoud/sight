import { describe, it, expect, beforeEach } from "vitest";
import { getToken, setToken, clearToken, api } from "./client";

describe("token management", () => {
  beforeEach(() => { localStorage.clear(); });
  it("returns null when no token set", () => { expect(getToken()).toBeNull(); });
  it("stores and retrieves a token", () => { setToken("abc"); expect(getToken()).toBe("abc"); });
  it("clears the token", () => { setToken("abc"); clearToken(); expect(getToken()).toBeNull(); });
  it("api instance exists", () => { expect(api).toBeDefined(); expect(api.defaults.timeout).toBe(30000); });
});
