import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NavigationProgress } from "@/components/NavigationProgress";
import { act, render } from "./render";

const nav = vi.hoisted(() => ({ pathname: "/home", params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  usePathname: () => nav.pathname,
  useSearchParams: () => nav.params,
}));

function montar() {
  const vista = render(
    <>
      <NavigationProgress />
      <a href="/search">Buscar</a>
      <a href="/home">Inicio</a>
      <a href="/search" target="_blank">
        Afuera
      </a>
    </>
  );
  const barra = () => vista.container.querySelector("[data-estado]")!.getAttribute("data-estado");
  const clic = (texto: string, opciones: MouseEventInit = {}) =>
    act(() => {
      const enlace = vista.getByText(texto);
      // Como `next/link`: navega por su cuenta, sin recargar la página.
      enlace.addEventListener("click", (evento) => evento.preventDefault(), { once: true });
      enlace.dispatchEvent(
        new MouseEvent("click", { bubbles: true, cancelable: true, ...opciones })
      );
    });
  return { vista, barra, clic };
}

describe("barra de navegación", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    nav.pathname = "/home";
    window.history.replaceState(null, "", "/home");
  });
  afterEach(() => vi.useRealTimers());

  it("aparece al tocar un enlace interno y se completa al llegar la página", () => {
    const { vista, barra, clic } = montar();
    clic("Buscar");
    expect(barra()).toBe("quieta");
    act(() => vi.advanceTimersByTime(120));
    expect(barra()).toBe("cargando");

    nav.pathname = "/search";
    vista.rerender(
      <>
        <NavigationProgress />
      </>
    );
    expect(barra()).toBe("terminando");
    act(() => vi.advanceTimersByTime(400));
    expect(barra()).toBe("quieta");
  });

  it("una navegación rápida no la muestra", () => {
    const { vista, barra, clic } = montar();
    clic("Buscar");
    nav.pathname = "/search";
    vista.rerender(<NavigationProgress />);
    act(() => vi.advanceTimersByTime(500));
    expect(barra()).toBe("quieta");
  });

  it("no arranca con la misma página, otra pestaña o un clic con Ctrl", () => {
    const { barra, clic } = montar();
    clic("Inicio");
    clic("Afuera");
    clic("Buscar", { ctrlKey: true });
    act(() => vi.advanceTimersByTime(500));
    expect(barra()).toBe("quieta");
  });

  it("no arranca si el aviso de cambios sin guardar frena el clic", () => {
    // Así frena `NavigationGuard`: captura en `document` y corta la propagación.
    const frenar = (evento: Event) => {
      evento.preventDefault();
      evento.stopImmediatePropagation();
    };
    document.addEventListener("click", frenar, true);
    const { barra, clic } = montar();
    clic("Buscar");
    act(() => vi.advanceTimersByTime(500));
    document.removeEventListener("click", frenar, true);
    expect(barra()).toBe("quieta");
  });

  it("si la página nunca llega, no queda colgada", () => {
    const { barra, clic } = montar();
    clic("Buscar");
    act(() => vi.advanceTimersByTime(120));
    expect(barra()).toBe("cargando");
    act(() => vi.advanceTimersByTime(15_000));
    act(() => vi.advanceTimersByTime(400));
    expect(barra()).toBe("quieta");
  });
});
