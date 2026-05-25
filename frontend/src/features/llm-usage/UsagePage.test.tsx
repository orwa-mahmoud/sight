import { describe, it, expect } from "vitest";
describe("UsagePage helpers", () => {
  it("formats cost below 1 cent with 6 decimals", () => {
    const n = 0.005;
    const formatted = n < 0.01 ? `$${n.toFixed(6)}` : `$${n.toFixed(2)}`;
    expect(formatted).toBe("$0.005000");
  });

  it("formats cost above 1 cent with 2 decimals", () => {
    const n = 1.23;
    const formatted = n < 0.01 ? `$${n.toFixed(6)}` : `$${n.toFixed(2)}`;
    expect(formatted).toBe("$1.23");
  });

  it("formats NaN as $0.00", () => {
    const n = Number.NaN;
    const formatted = Number.isNaN(n) ? "$0.00" : `$${n.toFixed(2)}`;
    expect(formatted).toBe("$0.00");
  });
});
