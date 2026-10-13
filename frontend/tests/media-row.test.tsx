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

  it("mientras carga muestra cinco esqueletos y ninguna tarjeta", () => {
    render(<MediaRow title="New releases" items={[]} showType loading />, { locale: "en" });

    const fila = screen.getByRole("region", { name: "New releases" });
    expect(fila).toHaveAttribute("aria-busy", "true");
    expect(within(fila).queryAllByRole("link")).toHaveLength(0);
    expect(fila.querySelectorAll("[data-skeleton]")).toHaveLength(5);
  });

  it("las flechas desplazan la fila casi un ancho hacia cada lado", () => {
    // jsdom no calcula tamaños: se fija el ancho visible de la fila a mano.
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1000);
    const scrollBy = vi.fn();
    Element.prototype.scrollBy = scrollBy;
    render(<MediaRow title="Trending this week" items={titulos} showType />, { locale: "en" });

    fireEvent.click(screen.getByRole("button", { name: "Next in Trending this week" }));
    fireEvent.click(screen.getByRole("button", { name: "Previous in Trending this week" }));

    expect(scrollBy).toHaveBeenNthCalledWith(1, expect.objectContaining({ left: 900 }));
    expect(scrollBy).toHaveBeenNthCalledWith(2, expect.objectContaining({ left: -900 }));
  });
});
