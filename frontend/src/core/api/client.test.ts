import { describe, it, expect, beforeEach } from "vitest";
import { getToken, setToken, clearToken } from "./client";

describe("token management", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when no token set", () => {
    expect(getToken()).toBeNull();
  });

  it("stores and retrieves a token", () => {
    setToken("abc123");
    expect(getToken()).toBe("abc123");
  });

  it("clears the token", () => {
    setToken("abc123");
    clearToken();
    expect(getToken()).toBeNull();
  });
});
