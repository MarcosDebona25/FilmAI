import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
HTMLDialogElement.prototype.showModal = function () {
  this.setAttribute("open", "");
  this.querySelector<HTMLElement>("button, input, textarea")?.focus();
};
HTMLDialogElement.prototype.close = function () {
  this.removeAttribute("open");
};
globalThis.IntersectionObserver = class {
  observe() {}
  disconnect() {}
  unobserve() {}
} as unknown as typeof IntersectionObserver;

globalThis.ResizeObserver = class {
  observe() {}
  disconnect() {}
  unobserve() {}
} as unknown as typeof ResizeObserver;

// jsdom no trae `scrollIntoView` (no hay layout): un stub para poder espiarlo.
Element.prototype.scrollIntoView = function () {};

// jsdom tampoco trae `matchMedia`: por defecto nada coincide («sin preferencia de movimiento»).
window.matchMedia ??= ((query: string) => ({
  matches: false,
  media: query,
})) as typeof window.matchMedia;
