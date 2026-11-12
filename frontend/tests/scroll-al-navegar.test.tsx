import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// `vi.hoisted` crea la variable antes que el `vi.mock` de abajo, que Vitest sube
// al principio del archivo: así el mock puede leer la ruta que fija cada test.
const ruta = vi.hoisted(() => ({ actual: "/terms" }));
vi.mock("next/navigation", () => ({ usePathname: () => ruta.actual }));

import { ScrollArribaAlNavegar } from "@/components/ScrollArribaAlNavegar";

describe("ScrollArribaAlNavegar", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window, "scrollY", { value: 0, configurable: true });
    ruta.actual = "/terms";
    window.history.replaceState(null, "", "/terms");
  });

  function navegarA(nueva: string, rerender: (ui: React.ReactElement) => void) {
    ruta.actual = nueva;
    window.history.pushState(null, "", nueva);
    rerender(<ScrollArribaAlNavegar />);
  }

  it("al entrar no mueve nada: el navegador restaura el scroll al recargar", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});

    render(<ScrollArribaAlNavegar />);

    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("al ir a otra página la lleva arriba de todo", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const { rerender } = render(<ScrollArribaAlNavegar />);

    navegarA("/search", rerender);

    expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "instant" });
  });

  // Simula que el usuario bajó hasta `y` en la página que está en la URL.
  function bajarA(y: number) {
    Object.defineProperty(window, "scrollY", { value: y, configurable: true });
    window.dispatchEvent(new Event("scroll"));
  }

  function volverA(anterior: string, rerender: (ui: React.ReactElement) => void) {
    window.history.replaceState(null, "", anterior);
    window.dispatchEvent(new PopStateEvent("popstate"));
    ruta.actual = anterior;
    rerender(<ScrollArribaAlNavegar />);
  }

  it("con atrás devuelve el scroll que había en esa página", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const { rerender } = render(<ScrollArribaAlNavegar />);
    bajarA(900);
    navegarA("/search", rerender);
    // El navegador recorta el scroll al alto de /search antes de que vuelva /terms.
    bajarA(534);

    volverA("/terms", rerender);

    expect(scrollTo).toHaveBeenLastCalledWith({ top: 900, left: 0, behavior: "instant" });
  });

  it("si atrás solo cambia la búsqueda (?q=) no mueve la página", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const { rerender } = render(<ScrollArribaAlNavegar />);
    window.history.pushState(null, "", "/terms?q=a");

    window.history.replaceState(null, "", "/terms");
    window.dispatchEvent(new PopStateEvent("popstate"));
    rerender(<ScrollArribaAlNavegar />);
    navegarA("/lists", rerender);

    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 0, left: 0, behavior: "instant" });
  });

  it("después de un atrás, la navegación siguiente vuelve a llevar arriba", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const { rerender } = render(<ScrollArribaAlNavegar />);
    navegarA("/search", rerender);
    volverA("/terms", rerender);
    scrollTo.mockClear();

    navegarA("/lists", rerender);

    expect(scrollTo).toHaveBeenCalledTimes(1);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 0, left: 0, behavior: "instant" });
  });

  it("con un ancla (#) no mueve nada: el salto a la sección lo hace el navegador", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const { rerender } = render(<ScrollArribaAlNavegar />);

    navegarA("/settings#t-idioma", rerender);

    expect(scrollTo).not.toHaveBeenCalled();
  });
});
