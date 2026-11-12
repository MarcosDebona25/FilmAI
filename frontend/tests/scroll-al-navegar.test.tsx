import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// `vi.hoisted` crea la variable antes que el `vi.mock` de abajo, que Vitest sube
// al principio del archivo: así el mock puede leer la ruta que fija cada test.
const ruta = vi.hoisted(() => ({ actual: "/terms" }));
vi.mock("next/navigation", () => ({ usePathname: () => ruta.actual }));

import { ScrollArribaAlNavegar } from "@/components/ScrollArribaAlNavegar";

describe("ScrollArribaAlNavegar", () => {
  beforeEach(() => {
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

  it("con atrás o adelante no mueve nada: Next y el navegador restauran el scroll", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const { rerender } = render(<ScrollArribaAlNavegar />);

    window.dispatchEvent(new PopStateEvent("popstate"));
    ruta.actual = "/search";
    rerender(<ScrollArribaAlNavegar />);

    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("después de un atrás, la navegación siguiente vuelve a llevar arriba", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const { rerender } = render(<ScrollArribaAlNavegar />);
    window.dispatchEvent(new PopStateEvent("popstate"));
    ruta.actual = "/search";
    rerender(<ScrollArribaAlNavegar />);

    navegarA("/lists", rerender);

    expect(scrollTo).toHaveBeenCalledTimes(1);
  });

  it("con un ancla (#) no mueve nada: el salto a la sección lo hace el navegador", () => {
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const { rerender } = render(<ScrollArribaAlNavegar />);

    navegarA("/settings#t-idioma", rerender);

    expect(scrollTo).not.toHaveBeenCalled();
  });
});
