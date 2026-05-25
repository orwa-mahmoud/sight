import { describe, it, expect } from "vitest";

describe("UsagePage helpers", () => {
  function formatCost(usd: string): string {
    const n = Number(usd);
    if (Number.isNaN(n)) return "$0.00";
    return n < 0.01 ? "$" + n.toFixed(6) : "$" + n.toFixed(2);
  }
  function formatTokens(n: number): string {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return String(n);
  }

  it("formats cost below 1 cent", () => { expect(formatCost("0.005")).toBe("$0.005000"); });
  it("formats cost above 1 cent", () => { expect(formatCost("1.23")).toBe("$1.23"); });
  it("formats NaN", () => { expect(formatCost("not")).toBe("$0.00"); });
  it("formats zero", () => { expect(formatCost("0")).toBe("$0.000000"); });
  it("formats tokens K", () => { expect(formatTokens(1500)).toBe("1.5K"); });
  it("formats tokens M", () => { expect(formatTokens(2500000)).toBe("2.5M"); });
  it("formats tokens small", () => { expect(formatTokens(42)).toBe("42"); });
});
