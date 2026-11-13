import { afterEach, describe, expect, it, vi } from "vitest";

import { MediaRow } from "@/components/features/MediaRow";
import { normalizeTitles } from "@/lib/catalog";
import { fireEvent, render, screen, within } from "./render";
import { insidious, reacher } from "./catalog-fixtures";

const titulos = normalizeTitles([insidious, reacher]);

afterEach(() => vi.restoreAllMocks());

describe("MediaRow", () => {
  it("muestra el título, la descripción y una tarjeta por título", () => {
    render(
      <MediaRow
        title="Trending this week"
        description="Most viewed on TMDB in the last seven days"
        items={titulos}
        showType
      />,
      { locale: "en" }
    );

    const fila = screen.getByRole("region", { name: "Trending this week" });
    expect(within(fila).getByRole("heading", { level: 2 })).toHaveTextContent("Trending this week");
    expect(within(fila).getByText("Most viewed on TMDB in the last seven days")).toBeVisible();
    const lista = within(fila).getByRole("list", {
      name: "Trending this week, swipe to see more",
    });
    expect(within(lista).getAllByRole("listitem")).toHaveLength(2);
  });

  it("vacía y sin cargar no ocupa lugar", () => {
    const { container } = render(<MediaRow title="Recommended for you" items={[]} showType />, {
      locale: "en",
    });

    expect(container).toBeEmptyDOMElement();
  });

  it("mientras carga muestra siete esqueletos (la página más ancha) y ninguna tarjeta", () => {
    render(<MediaRow title="New releases" items={[]} showType loading />, { locale: "en" });

    const fila = screen.getByRole("region", { name: "New releases" });
    expect(fila).toHaveAttribute("aria-busy", "true");
    expect(within(fila).queryAllByRole("link")).toHaveLength(0);
    expect(fila.querySelectorAll("[data-skeleton]")).toHaveLength(7);
  });

  describe("flechas a los costados", () => {
    // jsdom no calcula tamaños ni scroll: se fijan a mano. `scrollWidth` y
    // `clientWidth` valen para todos los elementos; `scrollLeft` se escribe en la lista.
    function medidas({ ancho = 1000, total = 3000 } = {}) {
      vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(ancho);
      vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(total);
    }
    function scrollear(lista: HTMLElement, izquierda: number) {
      lista.scrollLeft = izquierda;
      fireEvent.scroll(lista);
    }
    const siguiente = () => screen.queryByRole("button", { name: "Next in Trending this week" });
    const anterior = () => screen.queryByRole("button", { name: "Previous in Trending this week" });
    const filaDeTendencias = () => <MediaRow title="Trending this week" items={titulos} showType />;

    it("al principio solo hay flecha derecha", () => {
      medidas();
      render(filaDeTendencias(), { locale: "en" });

      expect(anterior()).toBeNull();
      expect(siguiente()).toBeInTheDocument();
    });

    it("en el medio hay las dos y al final solo la izquierda", () => {
      medidas();
      render(filaDeTendencias(), { locale: "en" });
      const lista = screen.getByRole("list");

      scrollear(lista, 1000);
      expect(anterior()).toBeInTheDocument();
      expect(siguiente()).toBeInTheDocument();

      scrollear(lista, 2000); // 2000 + 1000 de ancho visible = 3000: llegó al final
      expect(anterior()).toBeInTheDocument();
      expect(siguiente()).toBeNull();
    });

    it("las flechas van antes de las tarjetas en el orden de tabulación", () => {
      medidas();
      render(filaDeTendencias(), { locale: "en" });
      scrollear(screen.getByRole("list"), 1000);

      const lista = screen.getByRole("list");
      const antes = (a: Node, b: Node) =>
        Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
      expect(antes(anterior()!, lista)).toBe(true);
      expect(antes(siguiente()!, lista)).toBe(true);
    });

    it("si todo entra sin scroll no hay ninguna flecha", () => {
      medidas({ ancho: 1000, total: 1000 });
      render(filaDeTendencias(), { locale: "en" });

      expect(anterior()).toBeNull();
      expect(siguiente()).toBeNull();
    });

    it("las flechas desplazan la fila exactamente una página (ancho visible + gap)", () => {
      medidas();
      const original = window.getComputedStyle;
      vi.spyOn(window, "getComputedStyle").mockImplementation((elemento) => {
        const estilo = original(elemento);
        return elemento.tagName === "UL"
          ? ({ ...estilo, columnGap: "20px" } as CSSStyleDeclaration)
          : estilo;
      });
      const scrollBy = vi.fn();
      Element.prototype.scrollBy = scrollBy;
      render(filaDeTendencias(), { locale: "en" });
      scrollear(screen.getByRole("list"), 1000);

      fireEvent.click(siguiente()!);
      fireEvent.click(anterior()!);

      expect(scrollBy).toHaveBeenNthCalledWith(1, expect.objectContaining({ left: 1020 }));
      expect(scrollBy).toHaveBeenNthCalledWith(2, expect.objectContaining({ left: -1020 }));
    });

    it("las flechas solo se muestran desde md y con el mouse o el teclado encima", () => {
      medidas();
      render(filaDeTendencias(), { locale: "en" });

      const clases = siguiente()!.className;
      expect(clases.split(" ")).toEqual(expect.arrayContaining(["hidden", "md:flex"]));
      expect(clases).toContain("opacity-0");
      // Invisible no es clicable: en una tablet sin hover, tocar el borde del póster abre la ficha.
      expect(clases).toContain("pointer-events-none");
      expect(clases).toContain("group-hover/fila:pointer-events-auto");
      expect(clases).toContain("group-hover/fila:opacity-100");
      expect(clases).toContain("focus-visible:opacity-100");
      expect(clases).toContain("motion-reduce:transition-none");
    });
  });

  it("con `seeAll` el encabezado trae un enlace al listado completo", () => {
    render(
      <MediaRow
        title="Watchlist"
        items={titulos}
        showType
        seeAll={{ href: "/lists/7", label: "See all" }}
      />,
      { locale: "en" }
    );

    expect(screen.getByRole("link", { name: "See all" })).toHaveAttribute("href", "/lists/7");
  });
});
