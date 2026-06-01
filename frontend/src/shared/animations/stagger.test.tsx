import { render } from "@testing-library/react";
import gsap from "gsap";
import { useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useStaggerIn } from "./stagger";

function setMatchMedia(matches: boolean) {
  Object.defineProperty(globalThis, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

afterEach(() => {
  setMatchMedia(false);
  vi.restoreAllMocks();
});

function Staggered() {
  const ref = useRef<HTMLDivElement>(null);
  useStaggerIn(ref, ".item", []);
  return (
    <div ref={ref}>
      <span className="item">a</span>
      <span className="item">b</span>
    </div>
  );
}

describe("useStaggerIn", () => {
  it("animates matching elements when motion is allowed", () => {
    setMatchMedia(false);
    const spy = vi.spyOn(gsap, "from").mockReturnValue({} as ReturnType<typeof gsap.from>);
    render(<Staggered />);
    expect(spy).toHaveBeenCalledOnce();
  });

  it("skips animation when prefers-reduced-motion is set", () => {
    setMatchMedia(true); // reduce
    const spy = vi.spyOn(gsap, "from").mockReturnValue({} as ReturnType<typeof gsap.from>);
    render(<Staggered />);
    expect(spy).not.toHaveBeenCalled();
  });

  it("never throws if gsap fails", () => {
    setMatchMedia(false);
    vi.spyOn(gsap, "from").mockImplementation(() => {
      throw new Error("gsap boom");
    });
    expect(() => render(<Staggered />)).not.toThrow();
  });
});
