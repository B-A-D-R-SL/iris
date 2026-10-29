// AI contribution: 50% or more AI-generated
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import i18n from "../shared/i18n";

// Mock matchMedia because jsdom does not implement it.
// Required by Mantine UI's color scheme detection.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Also missing from jsdom and used by Mantine menus, pickers and app shell.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverStub;
window.HTMLElement.prototype.scrollIntoView = () => {};
// Growing text areas (Textarea autosize) re-measure when web fonts load.
Object.defineProperty(document, "fonts", {
  value: { addEventListener: vi.fn(), removeEventListener: vi.fn(), ready: Promise.resolve() },
});

// Every test starts in French (the default), with the real fetch and a clean DOM.
afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  await i18n.changeLanguage("fr");
});
