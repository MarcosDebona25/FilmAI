import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { ListSuggestions } from "@/components/features/lists/ListSuggestions";
import type { ItemLista, PaginaSugerencias, Sugerencia } from "@/lib/lists";
import { render, screen, waitFor, within } from "./render";

const estado = vi.hoisted(() => ({
  // Lo que responde cada página pedida; una función permite cambiarla entre pedidos.
  paginas: {} as Record<number, unknown>,
  fallar: null as "sugerencias" | "alta" | null,
  pedidos: [] as { path: string; method: string; body?: unknown }[],
}));

vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...real,
    apiFetch: vi.fn(async (path: string, opciones: { method?: string; body?: unknown } = {}) => {
      const method = opciones.method ?? "GET";
      estado.pedidos.push({ path, method, body: opciones.body });
      if (method === "GET") {
        if (estado.fallar === "sugerencias") throw new real.ApiError(500, { code: "server_error" });
        const numero = Number(new URL(path, "http://x").searchParams.get("pagina"));
        return structuredClone(estado.paginas[numero]);
      }
      if (estado.fallar === "alta") throw new real.ApiError(409, { code: "list_item_duplicated" });
      const cuerpo = opciones.body as { id_tmdb: number; tipo: "movie" | "tv" };
      return {
        item_id: 900 + cuerpo.id_tmdb,
        fecha_agregado: "2026-11-15T00:00:00Z",
        id_tmdb: cuerpo.id_tmdb,
        tipo: cuerpo.tipo,
        titulo: `Sugerida ${cuerpo.id_tmdb}`,
        poster: null,
        anio: 2020,
        calificacion_promedio: 7.6,
        disponible: true,
      } satisfies ItemLista;
    }),
  };
});

function sugerencia(n: number, extra: Partial<Sugerencia> = {}): Sugerencia {
  return {
    id_tmdb: n,
    tipo: "movie",
    titulo: `Sugerida ${n}`,
    poster: null,
    anio: 2020,
    calificacion_promedio: 7.6,
    origen: "catalogo",
    ...extra,
  };
}
function pagina(
  numeros: number[],
  extra: Partial<Omit<PaginaSugerencias, "results">> = {}
): PaginaSugerencias {
  return {
    results: numeros.map((n) => sugerencia(n)),
    pagina: 1,
    paginas: 1,
    nombre_usado: true,
    ...extra,
  };
}

const lecturas = () => estado.pedidos.filter((p) => p.method === "GET").map((p) => p.path);
const titulos = () =>
  within(screen.getByRole("region", { name: "Suggested for this list" }))
    .getAllByRole("listitem")
    .map((li) => within(li).getAllByRole("link")[1].textContent);
// El botón está dos veces en el DOM (arriba en escritorio, abajo en celular);
// el CSS muestra uno solo y jsdom no aplica CSS.
const verMas = () => screen.queryAllByRole("button", { name: "Show more suggestions" });

function banda(extra: Partial<Parameters<typeof ListSuggestions>[0]> = {}) {
  const onAgregada = vi.fn();
  const props = {
    listaId: 7,
    nombre: "Sci Fi",
    cantidad: 12,
    revision: 0,
    visible: true,
    onAgregada,
    ...extra,
  };
  const vista = render(<ListSuggestions {...props} />, { locale: "en" });
  return {
    onAgregada,
    cambiar: (cambios: Partial<typeof props>) =>
      vista.rerender(<ListSuggestions {...props} {...cambios} />),
  };
}

beforeEach(() => {
  estado.paginas = { 1: pagina([1, 2, 3]) };
  estado.fallar = null;
  estado.pedidos = [];
  vi.mocked(toast.success).mockClear();
  vi.mocked(toast.error).mockClear();
});

describe("Banda de sugerencias de una lista", () => {
  it("dibuja el título, la frase y cada sugerencia con su enlace, sus datos y «+ Add»", async () => {
    estado.paginas[1] = {
      ...pagina([1]),
      results: [sugerencia(1, { titulo: "Arrival", anio: 2016 }), sugerencia(2, { tipo: "tv" })],
    };
    banda();

    const region = await screen.findByRole("region", { name: "Suggested for this list" });
    expect(
      within(region).getByText(
        "Based on its 12 titles and its name, without what you already watched."
      )
    ).toBeInTheDocument();
    expect(lecturas()).toEqual(["/api/lists/7/suggestions/?pagina=1"]);
    const [primera, segunda] = within(region).getAllByRole("listitem");
    expect(within(primera).getByRole("link", { name: "Arrival" })).toHaveAttribute(
      "href",
      "/movie/1?from=list-7"
    );
    expect(within(primera).getByText(/Movie · 2016/)).toBeInTheDocument();
    expect(within(primera).getByText("TMDB rating: 7.6 out of 10")).toBeInTheDocument();
    expect(
      within(primera).getByRole("button", { name: "Add Arrival to Sci Fi" })
    ).toHaveTextContent("Add");
    expect(within(segunda).getByRole("link", { name: "Sugerida 2" })).toHaveAttribute(
      "href",
      "/tv/2?from=list-7"
    );
    expect(within(segunda).getByText(/TV show · 2020/)).toBeInTheDocument();
  });

  it("no nombra el nombre de la lista si no entró en el cálculo, y concuerda con un solo título", async () => {
    estado.paginas[1] = pagina([1], { nombre_usado: false });
    banda({ cantidad: 1 });

    expect(
      await screen.findByText("Based on its 1 title, without what you already watched.")
    ).toBeInTheDocument();
  });

  it("no se dibuja si no hay nada para sugerir", async () => {
    estado.paginas[1] = pagina([], { paginas: 0 });
    banda();

    await waitFor(() => expect(lecturas()).toHaveLength(1));
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it("no se dibuja si el pedido falla", async () => {
    estado.fallar = "sugerencias";
    banda();

    await waitFor(() => expect(lecturas()).toHaveLength(1));
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("no pide nada hasta ser visible y después no vuelve a pedir", async () => {
    const { cambiar } = banda({ visible: false });

    expect(lecturas()).toEqual([]);
    expect(screen.queryByRole("region")).not.toBeInTheDocument();

    cambiar({ visible: true });
    expect(await screen.findByRole("region")).toBeInTheDocument();
    cambiar({ visible: false });
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    cambiar({ visible: true });

    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(lecturas()).toHaveLength(1);
  });
});

describe("«Show more suggestions»", () => {
  it("no aparece cuando hay una sola página", async () => {
    banda();

    await screen.findByRole("region");
    expect(verMas()).toEqual([]);
  });

  it("pide la página siguiente, agrega lo nuevo debajo y se oculta en la última", async () => {
    const usuario = userEvent.setup();
    estado.paginas = {
      1: pagina([1, 2], { paginas: 3 }),
      2: pagina([3, 4], { pagina: 2, paginas: 3 }),
      3: pagina([5], { pagina: 3, paginas: 3 }),
    };
    banda();
    await screen.findByRole("region");

    await usuario.click(verMas()[0]);
    await waitFor(() => expect(titulos()).toHaveLength(4));
    expect(titulos()).toEqual(["Sugerida 1", "Sugerida 2", "Sugerida 3", "Sugerida 4"]);
    expect(verMas()).not.toEqual([]);

    await usuario.click(verMas()[0]);
    await waitFor(() => expect(titulos()).toHaveLength(5));
    expect(lecturas()).toEqual([
      "/api/lists/7/suggestions/?pagina=1",
      "/api/lists/7/suggestions/?pagina=2",
      "/api/lists/7/suggestions/?pagina=3",
    ]);
    expect(verMas()).toEqual([]);
    // El botón ya no está: el foco pasa a lo primero que se agregó.
    await waitFor(() => expect(screen.getByRole("link", { name: "Sugerida 5" })).toHaveFocus());
  });

  it("no repite un título que ya mostró", async () => {
    const usuario = userEvent.setup();
    estado.paginas = {
      1: pagina([1, 2], { paginas: 2 }),
      2: pagina([2, 3], { pagina: 2, paginas: 2 }),
    };
    banda();
    await screen.findByRole("region");

    await usuario.click(verMas()[0]);

    await waitFor(() => expect(titulos()).toEqual(["Sugerida 1", "Sugerida 2", "Sugerida 3"]));
  });

  it("si falla, avisa y deja el botón para reintentar", async () => {
    const usuario = userEvent.setup();
    estado.paginas = { 1: pagina([1], { paginas: 2 }) };
    banda();
    await screen.findByRole("region");
    estado.fallar = "sugerencias";

    await usuario.click(verMas()[0]);

    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
    expect(titulos()).toEqual(["Sugerida 1"]);
    expect(verMas()[0]).toBeEnabled();
  });

  it("si la lista cambió, vuelve a la página 1 del pool nuevo y saltea lo ya mostrado", async () => {
    const usuario = userEvent.setup();
    estado.paginas = { 1: pagina([1, 2], { paginas: 2 }) };
    const { cambiar } = banda();
    await screen.findByRole("region");

    // Agregar o quitar un título cambia la firma del pool en el backend: otro orden.
    cambiar({ revision: 1, cantidad: 13 });
    estado.paginas = {
      1: pagina([2, 1], { paginas: 2 }),
      2: pagina([8, 9], { pagina: 2, paginas: 2 }),
    };
    await usuario.click(verMas()[0]);

    await waitFor(() =>
      expect(titulos()).toEqual(["Sugerida 1", "Sugerida 2", "Sugerida 8", "Sugerida 9"])
    );
    // La página 1 no traía nada nuevo: se pidió la 2 sin otro clic.
    expect(lecturas().slice(1)).toEqual([
      "/api/lists/7/suggestions/?pagina=1",
      "/api/lists/7/suggestions/?pagina=2",
    ]);
    expect(verMas()).toEqual([]);
  });
});

describe("«+ Add»", () => {
  it("agrega el título a la lista, lo saca de la banda y avisa a la pantalla", async () => {
    const usuario = userEvent.setup();
    const { onAgregada } = banda();
    await screen.findByRole("region");

    await usuario.click(screen.getByRole("button", { name: "Add Sugerida 2 to Sci Fi" }));

    await waitFor(() => expect(titulos()).toEqual(["Sugerida 1", "Sugerida 3"]));
    expect(estado.pedidos.at(-1)).toEqual({
      path: "/api/lists/7/items/",
      method: "POST",
      body: { id_tmdb: 2, tipo: "movie" },
    });
    expect(onAgregada).toHaveBeenCalledWith(expect.objectContaining({ item_id: 902, id_tmdb: 2 }));
    // El botón desapareció: el foco pasa al «+ Add» que quedó en su lugar.
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Add Sugerida 3 to Sci Fi" })).toHaveFocus()
    );
  });

  it("al agregar la última sugerencia, la banda desaparece", async () => {
    const usuario = userEvent.setup();
    estado.paginas[1] = pagina([1]);
    banda();
    await screen.findByRole("region");

    await usuario.click(screen.getByRole("button", { name: "Add Sugerida 1 to Sci Fi" }));

    await waitFor(() => expect(screen.queryByRole("region")).not.toBeInTheDocument());
  });

  it("si la API rechaza el alta, muestra el error por código y la sugerencia queda", async () => {
    const usuario = userEvent.setup();
    estado.fallar = null;
    const { onAgregada } = banda();
    await screen.findByRole("region");
    estado.fallar = "alta";

    await usuario.click(screen.getByRole("button", { name: "Add Sugerida 1 to Sci Fi" }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("This movie or TV show is already in the list.")
    );
    expect(titulos()).toEqual(["Sugerida 1", "Sugerida 2", "Sugerida 3"]);
    expect(onAgregada).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Add Sugerida 1 to Sci Fi" })).toBeEnabled();
  });
});
