import { afterEach, describe, expect, it, vi } from "vitest";

import { SugerenciasLista } from "@/components/SugerenciasLista";
import type { Sugerencia } from "@/lib/sugerencias";
import { render, screen } from "./render";

// Se deja pasar `src` para ver qué ancho de TMDB pide cada modo.
vi.mock("next/image", () => ({
  default: ({
    alt,
    src,
    width,
    height,
  }: {
    alt: string;
    src: string;
    width: number;
    height: number;
  }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt={alt} src={src} width={width} height={height} />
  ),
}));

const SUGERENCIAS: Sugerencia[] = [
  {
    tipo: "person",
    id: 525,
    nombre: "Christopher Nolan",
    rol: "director",
    genero: "male",
    foto: null,
  },
  {
    tipo: "movie",
    id: 27205,
    titulo: "Inception",
    anio: 2010,
    poster: "https://image.tmdb.org/t/p/w92/y.jpg",
    nota: 8.4,
  },
];

function lista(props: { rica?: boolean; activaId?: string } = {}) {
  return (
    <SugerenciasLista
      id="lista"
      sugerencias={SUGERENCIAS}
      cargando={false}
      activaId={props.activaId}
      alElegir={() => {}}
      verTodo="nol"
      rica={props.rica}
    />
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("SugerenciasLista", () => {
  it("rica: el desplegable cabe en la ventana y se desplaza por dentro", () => {
    render(lista({ rica: true }), { locale: "en" });
    const caja = screen.getByRole("listbox");
    expect(caja).toHaveClass("max-h-[calc(100dvh-5rem)]", "overflow-y-auto");
  });

  it("rica: el póster se pide en w154; la compacta sigue con el w92 de la API", () => {
    const { unmount } = render(lista({ rica: true }), { locale: "en" });
    expect(screen.getByRole("option", { name: /Inception/ }).querySelector("img")).toHaveAttribute(
      "src",
      "https://image.tmdb.org/t/p/w154/y.jpg"
    );
    unmount();
    render(lista(), { locale: "en" });
    expect(screen.getByRole("option", { name: /Inception/ }).querySelector("img")).toHaveAttribute(
      "src",
      "https://image.tmdb.org/t/p/w92/y.jpg"
    );
  });

  it("las iniciales de dos letras son solo de la rica; la compacta deja la primera", () => {
    const { unmount } = render(lista({ rica: true }), { locale: "en" });
    expect(screen.getByRole("option", { name: /Christopher Nolan/ })).toHaveTextContent(
      "CNChristopher Nolan"
    );
    unmount();
    render(lista(), { locale: "en" });
    expect(screen.getByRole("option", { name: /Christopher Nolan/ })).toHaveTextContent(
      "CChristopher Nolan"
    );
  });

  it("la opción activa se acerca a la vista, sin animación si el sistema pide menos movimiento", () => {
    const espia = vi.spyOn(Element.prototype, "scrollIntoView");
    vi.stubGlobal("matchMedia", (query: string) => ({ matches: query.includes("reduce") }));
    const { rerender } = render(lista({ rica: true }), { locale: "en" });
    expect(espia).not.toHaveBeenCalled();

    rerender(lista({ rica: true, activaId: "sug-movie-27205" }));
    expect(espia).toHaveBeenCalledTimes(1);
    expect(espia.mock.contexts[0]).toBe(document.getElementById("sug-movie-27205"));
    expect(espia).toHaveBeenCalledWith({ block: "nearest", behavior: "auto" });
  });

  it("con movimiento permitido, el desplazamiento es suave", () => {
    const espia = vi.spyOn(Element.prototype, "scrollIntoView");
    vi.stubGlobal("matchMedia", () => ({ matches: false }));
    render(lista({ rica: true, activaId: "sug-all" }), { locale: "en" });
    expect(espia).toHaveBeenCalledWith({ block: "nearest", behavior: "smooth" });
  });
});
