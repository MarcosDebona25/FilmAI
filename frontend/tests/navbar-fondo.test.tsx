import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useFondo } from "@/components/Navbar";

/**
 * El fondo de la navbar en escritorio, con un IntersectionObserver de mentira:
 * cada test decide si la imagen grande sigue debajo de la barra.
 */
type Aviso = (entradas: { isIntersecting: boolean }[]) => void;

let observadores: { aviso: Aviso; margen?: string; observados: Element[] }[] = [];

class ObservadorFalso {
  aviso: Aviso;
  margen?: string;
  observados: Element[] = [];
  constructor(aviso: Aviso, opciones?: IntersectionObserverInit) {
    this.aviso = aviso;
    this.margen = opciones?.rootMargin;
    observadores.push(this);
  }
  observe(elemento: Element) {
    this.observados.push(elemento);
  }
  disconnect() {}
  unobserve() {}
}

function pantalla(escritorio: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((consulta: string) => ({
      matches: escritorio,
      media: consulta,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
  );
}

function barraDe(alto: number) {
  const barra = document.createElement("header");
  Object.defineProperty(barra, "offsetHeight", { value: alto });
  return { current: barra };
}

function bajarA(y: number) {
  Object.defineProperty(window, "scrollY", { value: y, configurable: true });
  act(() => {
    window.dispatchEvent(new Event("scroll"));
  });
}

describe("useFondo de la navbar", () => {
  // Un `ref` por test, el mismo en cada render: como el `useRef` de la navbar.
  let barra84: ReturnType<typeof barraDe>;
  let barra60: ReturnType<typeof barraDe>;

  beforeEach(() => {
    barra84 = barraDe(84);
    barra60 = barraDe(60);
    observadores = [];
    vi.stubGlobal("IntersectionObserver", ObservadorFalso);
    bajarA(0);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  it("arriba de todo es transparente", () => {
    pantalla(true);
    const { result } = renderHook(() => useFondo(barra84, "/home"));

    expect(result.current).toBe("transparente");
  });

  it("con la imagen debajo es translúcido, y sólido cuando la imagen ya pasó", () => {
    pantalla(true);
    const imagen = document.createElement("div");
    imagen.setAttribute("data-imagen-bajo-navbar", "");
    document.body.append(imagen);
    const { result } = renderHook(() => useFondo(barra84, "/home"));
    const [observador] = observadores;
    // El margen negativo arriba descuenta la barra: la imagen «se ve» solo si
    // asoma por debajo de ella.
    expect(observador.margen).toBe("-84px 0px 0px 0px");
    expect(observador.observados).toEqual([imagen]);

    bajarA(150);
    act(() => observador.aviso([{ isIntersecting: true }]));
    expect(result.current).toBe("translucido");

    act(() => observador.aviso([{ isIntersecting: false }]));
    expect(result.current).toBe("solido");
  });

  it("reacciona aunque no haya scroll: la imagen cambia de alto al cargar", () => {
    pantalla(true);
    const imagen = document.createElement("div");
    imagen.setAttribute("data-imagen-bajo-navbar", "");
    document.body.append(imagen);
    bajarA(150);
    const { result } = renderHook(() => useFondo(barra84, "/home"));

    act(() => observadores[0].aviso([{ isIntersecting: false }]));

    expect(result.current).toBe("solido");
  });

  it("sin imagen grande, al bajar es sólido", () => {
    pantalla(true);
    const { result } = renderHook(() => useFondo(barra84, "/terms"));

    bajarA(200);

    expect(result.current).toBe("solido");
    expect(observadores).toHaveLength(0);
  });

  it("en celular no observa nada: los fondos son solo de escritorio", () => {
    pantalla(false);
    const imagen = document.createElement("div");
    imagen.setAttribute("data-imagen-bajo-navbar", "");
    document.body.append(imagen);
    const { result } = renderHook(() => useFondo(barra60, "/home"));

    bajarA(300);

    expect(observadores).toHaveLength(0);
    expect(result.current).toBe("transparente");
  });
});
