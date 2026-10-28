import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { MyReviewsView } from "@/components/features/reviews/MyReviewsView";
import type { MiResena } from "@/lib/reviews";
import { fireEvent, render, screen, waitFor, within } from "./render";

const INTERSTELLAR: MiResena = {
  id: 1,
  id_tmdb: 157336,
  tipo: "movie",
  titulo: "Interstellar",
  poster: "",
  valor: 9,
  fecha: "2026-10-03",
  texto: "La vi con mi papá.",
  moderada: false,
};
const AMERICAN_DAD: MiResena = {
  id: 2,
  id_tmdb: 1433,
  tipo: "tv",
  titulo: "American Dad!",
  poster: "",
  valor: 7,
  fecha: "2026-09-28",
  texto: null,
  moderada: false,
};

const estado = vi.hoisted(() => ({
  pagina: null as null | Record<string, unknown>,
  falla: false,
  /** Si está, `useSearchParams` queda atrasado respecto de la URL (como en Next al cambiarla). */
  paramsAtrasados: null as URLSearchParams | null,
  pedidos: [] as { path: string; method: string; body?: unknown }[],
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => estado.paramsAtrasados ?? new URLSearchParams(window.location.search),
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => ({ perfil: { pk: 1 }, error: null, recargar: vi.fn() }),
}));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...real,
    apiFetch: vi.fn(async (path: string, opciones: { method?: string; body?: unknown } = {}) => {
      const method = opciones.method ?? "GET";
      estado.pedidos.push({ path, method, body: opciones.body });
      if (method === "GET") {
        if (estado.falla) throw new real.ApiError(500, { code: "server_error" });
        return structuredClone(estado.pagina);
      }
      if (method === "PUT") return { id: 1, ...(opciones.body as object) };
      return undefined;
    }),
  };
});

let reemplazos: string[] = [];

function pagina(results: MiResena[], extra: Record<string, unknown> = {}) {
  return { total: results.length, total_propias: results.length, next: null, results, ...extra };
}

beforeEach(() => {
  estado.paramsAtrasados = null;
  window.history.replaceState(null, "", "/my-reviews");
  estado.pagina = pagina([INTERSTELLAR, AMERICAN_DAD]);
  estado.falla = false;
  estado.pedidos = [];
  reemplazos = [];
  vi.mocked(toast.success).mockClear();
  // Registra cada cambio de URL y lo aplica, como lo hace el navegador.
  const original = window.history.replaceState.bind(window.history);
  vi.spyOn(window.history, "replaceState").mockImplementation((estado, titulo, url) => {
    reemplazos.push(String(url));
    original(estado, titulo, url);
  });
});
afterEach(() => window.sessionStorage.clear());

const lecturas = () => estado.pedidos.filter((p) => p.method === "GET").map((p) => p.path);

describe("Calificaciones y reseñas", () => {
  it("pide la lista con los filtros de la URL y la muestra según el canvas", async () => {
    window.history.replaceState(null, "", "/my-reviews?type=movie&rating=8&sort=highest");
    render(<MyReviewsView />);
    expect(screen.getByRole("status", { name: "Cargando tus calificaciones…" })).toBeVisible();
    const titulo = await screen.findByRole("link", { name: "Interstellar" });
    expect(lecturas()).toEqual(["/api/reviews/mias/?clase=movie&nota_min=8&orden=nota-desc"]);
    // El título lleva a la ficha y su miga vuelve acá.
    expect(titulo).toHaveAttribute("href", "/movie/157336?from=reviews");
    // El nombre accesible dice «de 10»; el número suelto queda oculto al lector.
    expect(screen.getByText("Tu calificación: 9 de 10")).toHaveClass("sr-only");
    expect(screen.getByText("La vi con mi papá.")).toBeVisible();
    // Sin texto, «Agregar reseña» lleva a la ficha.
    expect(
      screen.getByRole("link", { name: "Agregar una reseña a American Dad!" })
    ).toHaveAttribute("href", "/tv/1433?from=reviews");
    expect(screen.getByLabelText("Calificación")).toHaveValue("8");
    expect(window.sessionStorage.getItem("filmai:ultimas-resenas")).toBe(
      "/my-reviews?type=movie&rating=8&sort=highest"
    );
  });

  it("un filtro cambia la URL y conserva los demás", async () => {
    window.history.replaceState(null, "", "/my-reviews?sort=oldest");
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "Interstellar" });
    fireEvent.change(screen.getByLabelText("Mostrar"), { target: { value: "without" } });
    expect(reemplazos.at(-1)).toBe("/my-reviews?review=without&sort=oldest");
  });

  it("el texto se aplica después de una pausa", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      render(<MyReviewsView />);
      fireEvent.change(screen.getByRole("searchbox", { name: "Buscar por título" }), {
        target: { value: "inter" },
      });
      expect(reemplazos).toEqual([]);
      vi.advanceTimersByTime(350);
      expect(reemplazos).toEqual(["/my-reviews?q=inter"]);
    } finally {
      vi.useRealTimers();
    }
  });

  it("sin calificaciones invita a buscar y no muestra filtros", async () => {
    estado.pagina = pagina([]);
    render(<MyReviewsView />);
    expect(
      await screen.findByText("Todavía no calificaste ninguna película ni serie.")
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Buscar qué calificar" })).toHaveAttribute(
      "href",
      "/search"
    );
    expect(screen.queryByRole("search")).not.toBeInTheDocument();
  });

  it("sin coincidencias ofrece limpiar los filtros, conservando el orden", async () => {
    window.history.replaceState(null, "", "/my-reviews?q=zzz&review=with&sort=lowest");
    estado.pagina = pagina([], { total_propias: 4 });
    render(<MyReviewsView />);
    const aviso = await screen.findByText("Ninguna calificación coincide con estos filtros.");
    fireEvent.click(within(aviso.parentElement!).getByRole("button", { name: "Limpiar filtros" }));
    expect(reemplazos.at(-1)).toBe("/my-reviews?sort=lowest");
  });

  it("limpiar no deja que la espera del texto devuelva los filtros ya quitados", async () => {
    window.history.replaceState(null, "", "/my-reviews?q=zzz&type=tv&rating=8");
    // Next tarda en reflejar la URL nueva: lo renderizado sigue con los filtros viejos.
    estado.paramsAtrasados = new URLSearchParams("q=zzz&type=tv&rating=8");
    estado.pagina = pagina([], { total_propias: 4 });
    render(<MyReviewsView />);
    const aviso = await screen.findByText("Ninguna calificación coincide con estos filtros.");
    fireEvent.click(within(aviso.parentElement!).getByRole("button", { name: "Limpiar filtros" }));
    await new Promise((resolver) => setTimeout(resolver, 600));
    expect(window.location.search).toBe("");
  });

  it("en celular cada filtro es un chip que se puede quitar", async () => {
    window.history.replaceState(null, "", "/my-reviews?review=with&rating=lt5");
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "Interstellar" });
    expect(screen.getByRole("button", { name: "Filtros y orden, 2 activos" })).toBeVisible();
    expect(screen.getByText("Orden: Más recientes")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Quitar filtro Calificación Menos de 5" }));
    expect(reemplazos.at(-1)).toBe("/my-reviews?review=with");
  });

  it("la hoja de filtros aplica al momento y cierra con el total", async () => {
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "Interstellar" });
    fireEvent.click(screen.getByRole("button", { name: "Filtros y orden" }));
    const hoja = screen.getByRole("dialog", { name: "Filtros y orden" });
    fireEvent.click(within(hoja).getByRole("button", { name: "Series" }));
    expect(reemplazos.at(-1)).toBe("/my-reviews?type=tv");
    fireEvent.click(within(hoja).getByRole("radio", { name: "Mayor calificación" }));
    fireEvent.click(within(hoja).getByRole("button", { name: "Ver 2 resultados" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("si la carga falla, permite reintentar", async () => {
    estado.falla = true;
    render(<MyReviewsView />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No pudimos cargar tus calificaciones."
    );
    estado.falla = false;
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByRole("link", { name: "Interstellar" })).toBeVisible();
  });

  it("editar usa el diálogo de la ficha y actualiza la fila", async () => {
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "Interstellar" });
    fireEvent.click(screen.getAllByRole("button", { name: "Editar" })[0]);
    const dialogo = screen.getByRole("dialog", { name: "Editar calificación" });
    expect(within(dialogo).getByRole("radio", { name: "9 de 10" })).toBeChecked();
    fireEvent.change(within(dialogo).getByLabelText(/Reseña/), {
      target: { value: "Otra vez, mejor." },
    });
    fireEvent.click(within(dialogo).getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByText("Otra vez, mejor.")).toBeVisible();
    expect(estado.pedidos.at(-1)).toEqual({
      path: "/api/reviews/1/",
      method: "PUT",
      body: { texto: "Otra vez, mejor." },
    });
    expect(toast.success).toHaveBeenCalledWith("Reseña actualizada.");
  });

  it("borrar la reseña conserva la calificación", async () => {
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "Interstellar" });
    fireEvent.click(screen.getByRole("button", { name: "Más acciones para Interstellar" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Eliminar reseña" }));
    const confirmar = screen.getByRole("alertdialog", { name: "¿Eliminar reseña?" });
    fireEvent.click(within(confirmar).getByRole("button", { name: "Eliminar reseña" }));
    expect(
      await screen.findByRole("link", { name: "Agregar una reseña a Interstellar" })
    ).toBeVisible();
    expect(estado.pedidos.at(-1)).toMatchObject({
      path: "/api/reviews/1/texto/",
      method: "DELETE",
    });
    expect(toast.success).toHaveBeenCalledWith("Reseña eliminada.");
  });

  it("quitar la calificación saca la fila y lleva el foco al título", async () => {
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "American Dad!" });
    // Sin texto, el menú no ofrece borrar una reseña que no existe.
    fireEvent.click(screen.getByRole("button", { name: "Más acciones para American Dad!" }));
    expect(screen.getAllByRole("menuitem")).toHaveLength(1);
    fireEvent.click(screen.getByRole("menuitem", { name: "Quitar calificación" }));
    const confirmar = screen.getByRole("alertdialog", { name: "¿Quitar tu calificación?" });
    fireEvent.click(within(confirmar).getByRole("button", { name: "Quitar calificación" }));
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "American Dad!" })).not.toBeInTheDocument()
    );
    expect(estado.pedidos.at(-1)).toMatchObject({ path: "/api/reviews/2/", method: "DELETE" });
    expect(toast.success).toHaveBeenCalledWith("Calificación eliminada.");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { level: 1, name: "Calificaciones y reseñas" })
      ).toHaveFocus()
    );
  });

  it("moderada: explica por qué no se borra el texto y el menú no lo borra", async () => {
    estado.pagina = pagina([{ ...INTERSTELLAR, moderada: true }, AMERICAN_DAD]);
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "Interstellar" });
    expect(
      screen.getByText("Esta reseña fue moderada, así que no podés editar ni borrar su texto.")
    ).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Más acciones para Interstellar" }));
    const borrar = screen.getByRole("menuitem", { name: "Eliminar reseña" });
    expect(borrar).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(borrar);
    expect(screen.queryByRole("alertdialog")).toBeNull();

    // Quitar la calificación entera sigue disponible.
    expect(screen.getByRole("menuitem", { name: "Quitar calificación" })).not.toHaveAttribute(
      "aria-disabled"
    );
  });

  it("moderada: editar abre el diálogo con el texto de solo lectura", async () => {
    estado.pagina = pagina([{ ...INTERSTELLAR, moderada: true }]);
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "Interstellar" });
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));

    const dialogo = screen.getByRole("dialog", { name: "Editar calificación" });
    expect(within(dialogo).getByLabelText(/Reseña/)).toHaveAttribute("readonly");
  });

  it("moderada: en celular la hoja no borra el texto", async () => {
    estado.pagina = pagina([{ ...INTERSTELLAR, moderada: true }]);
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "Interstellar" });
    fireEvent.click(screen.getByRole("button", { name: "Acciones para Interstellar" }));
    const hoja = screen.getByRole("dialog", { name: /Interstellar/ });

    const borrar = within(hoja).getByRole("button", { name: "Eliminar reseña" });
    expect(borrar).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(borrar);
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("en celular las tres acciones están en una hoja", async () => {
    render(<MyReviewsView />);
    await screen.findByRole("link", { name: "Interstellar" });
    fireEvent.click(screen.getByRole("button", { name: "Acciones para Interstellar" }));
    const hoja = screen.getByRole("dialog", { name: /Interstellar/ });
    expect(
      within(hoja)
        .getAllByRole("button")
        .map((boton) => boton.textContent)
    ).toEqual(["Editar calificación y reseña", "Eliminar reseña", "Quitar calificación"]);
    fireEvent.click(within(hoja).getByRole("button", { name: "Editar calificación y reseña" }));
    expect(screen.getByRole("dialog", { name: "Editar calificación" })).toBeVisible();
  });
});
