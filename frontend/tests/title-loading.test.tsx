import { describe, expect, it } from "vitest";

import { TitleSkeleton } from "@/components/features/title/TitleSkeleton";
import LoadingMovie from "@/app/movie/[id]/loading";
import LoadingTv from "@/app/tv/[id]/loading";
import { render } from "./render";

// Next muestra `loading.tsx` en el instante del clic en una ficha (13/11/2026):
// tiene que ser el mismo esqueleto de `TitleView`, sin textos ni datos.
describe("loading de la ficha", () => {
  it.each([
    ["película", LoadingMovie],
    ["serie", LoadingTv],
  ])("la %s muestra el esqueleto de la ficha, ocupado y sin contenido", (_nombre, Loading) => {
    const { container } = render(<Loading />);

    const main = container.querySelector("main#contenido");
    expect(main).not.toBeNull();
    expect(main?.getAttribute("aria-busy")).toBe("true");
    // Sin título, sin imágenes ni enlaces: solo bloques de relleno.
    expect(container.querySelector("h1, img, a, button")).toBeNull();
    // La grilla de la ficha: póster, encabezado y acciones.
    expect(container.querySelectorAll(".aspect-\\[2\\/3\\]")).toHaveLength(1);
  });

  it("es el mismo árbol que el esqueleto compartido", () => {
    const a = render(<LoadingMovie />).container.innerHTML;
    const b = render(<TitleSkeleton />).container.innerHTML;

    expect(a).toBe(b);
  });
});
