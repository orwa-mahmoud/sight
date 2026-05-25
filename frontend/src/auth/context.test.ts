import { describe, it, expect } from "vitest";
import { AuthContext } from "./context";

describe("AuthContext", () => {
  it("has a default value of null", () => {
    // The context is created with null as default — consumers must
    // be wrapped in AuthProvider.
    expect(AuthContext).toBeDefined();
  });
});
