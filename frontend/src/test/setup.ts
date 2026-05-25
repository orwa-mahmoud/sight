import "@testing-library/jest-dom/vitest";

Object.defineProperty(document, "fonts", {
  value: {
    addEventListener: () => { /* noop */ },
    removeEventListener: () => { /* noop */ },
    ready: Promise.resolve([]),
  },
});

Object.defineProperty(globalThis, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => { /* noop */ },
    removeListener: () => { /* noop */ },
    addEventListener: () => { /* noop */ },
    removeEventListener: () => { /* noop */ },
    dispatchEvent: () => false,
  }),
});

class ResizeObserverMock {
  observe() { /* noop for test env */ }
  unobserve() { /* noop for test env */ }
  disconnect() { /* noop for test env */ }
}
globalThis.ResizeObserver = ResizeObserverMock;

// Mantine Combobox calls scrollIntoView on option elements; jsdom does not implement it.
Element.prototype.scrollIntoView = function () { /* noop for test env */ };
