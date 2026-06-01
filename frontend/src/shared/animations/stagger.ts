import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import type { RefObject } from "react";

/** True when the user asked for reduced motion (or in non-DOM environments). */
function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Fade/slide-in stagger for the elements matching `selector` within `scope`.
 * Runs on first paint and whenever `deps` change (e.g. a new page of rows).
 * Respects prefers-reduced-motion and never throws (defensive in test envs).
 */
export function useStaggerIn(
  scope: RefObject<HTMLElement | null>,
  selector: string,
  deps: readonly unknown[]
): void {
  useGSAP(
    () => {
      if (prefersReducedMotion()) return;
      const root = scope.current;
      if (!root) return;
      try {
        const items = root.querySelectorAll<HTMLElement>(selector);
        if (items.length === 0) return;
        gsap.from(items, {
          opacity: 0,
          y: 8,
          duration: 0.25,
          stagger: 0.02,
          ease: "power1.out",
          overwrite: true,
        });
      } catch {
        /* animation is non-essential — never break rendering */
      }
    },
    { scope, dependencies: [...deps] }
  );
}
