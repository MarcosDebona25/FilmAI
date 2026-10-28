import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReviewsSection } from "@/components/features/title/ReviewsSection";
import { fireEvent, render, screen, waitFor, within } from "./render";

const LARGA =
  "I saw it in theaters and watched it again at home: the docking scene is still one of the tensest I’ve ever seen. The music does half the work, and every time the organ theme comes back I get goosebumps. What I like most is that, underneath all the science, it’s a story about a father.";
const COMUNIDAD = [
  { nombre_usuario: "lucia.cine", avatar_id: 3, valor: 10, fecha: "2026-09-28", texto: LARGA },
  { nombre_usuario: "mfernandez", avatar_id: 5, valor: 8, fecha: "2026-09-21", texto: "Great." },
  { nombre_usuario: "nico", avatar_id: 7, valor: 4, fecha: "2026-09-10", texto: "Too long." },
].map((resena) => ({ ...resena, autor_dado_de_baja: false }));
/** Así llega la reseña de una cuenta dada de baja (decisión del 26/10/2026). */
const DE_BAJA = {
  nombre_usuario: null,
  avatar_id: null,
  autor_dado_de_baja: true,
  valor: 9,
  fecha: "2026-09-30",
  texto: "Still my favourite.",
};

const estado = vi.hoisted(() => ({
  perfil: null as null | Record<string, unknown>,
  llamadas: [] as string[],
  vacia: false,
  /** La primera reseña es de una cuenta dada de baja. */
  conBaja: false,
  /** Cuántos pedidos de la lista fallan antes de responder bien. */
  fallas: 0,
}));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
vi.mock("sonner", () => ({ toast }));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => ({ perfil: estado.perfil, avatares: [], cargando: false }),
}));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...real,
    apiFetch: vi.fn(async (path: string, opciones: { method?: string } = {}) => {
      estado.llamadas.push(`${opciones.method ?? "GET"} ${path}`);
      if (opciones.method === "DELETE") return undefined;
      if (estado.fallas > 0) {
        estado.fallas--;
        throw new real.ApiError(500, { code: "server_error", params: {}, errors: [] });
      }
      const query = new URL(path, "http://filmai.local").searchParams;
      if (estado.vacia)
        return { total: 0, total_comunidad: 0, next: null, previous: null, results: [] };
      let items: Record<string, unknown>[] = estado.conBaja
        ? [DE_BAJA, ...COMUNIDAD]
        : [...COMUNIDAD];
      if (query.get("nota_min"))
        items = items.filter((r) => Number(r.valor) >= Number(query.get("nota_min")));
      if (query.get("nota_max"))
        items = items.filter((r) => Number(r.valor) <= Number(query.get("nota_max")));
      if (query.get("orden") === "nota-asc")
        items.sort((a, b) => Number(a.valor) - Number(b.valor));
      // Primera página de 2 y un cursor para la segunda, como el backend.
      const cursor = query.get("cursor");
      const pagina = cursor ? items.slice(2) : items.slice(0, 2);
      return {
        total: items.length,
        total_comunidad: COMUNIDAD.length,
        next: !cursor && items.length > 2 ? `http://api/api/reviews/?${query}&cursor=abc` : null,
        previous: null,
        results: pagina,
      };
    }),
  };
});

const props = {
  tipo: "movie" as const,
  idTmdb: 157336,
  titulo: "Interstellar",
  mia: null,
  onEditar: vi.fn(),
  onTextoBorrado: vi.fn(),
};

beforeEach(() => {
  estado.perfil = null;
  estado.llamadas = [];
  estado.vacia = false;
  estado.conBaja = false;
  estado.fallas = 0;
});
afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("reseñas de la comunidad", () => {
  it("se leen sin sesión, con el total y de a una página", async () => {
    render(<ReviewsSection {...props} />, { locale: "en" });

    expect(
      await screen.findByRole("heading", { name: "From the community (3)" })
    ).toBeInTheDocument();
    expect(screen.getByText("@lucia.cine")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.queryByRole("heading", { name: "Your review" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Load more reviews" }));

    expect(await screen.findByText("@nico")).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(3);
    expect(estado.llamadas.at(-1)).toContain("cursor=abc");
    expect(screen.queryByRole("button", { name: "Load more reviews" })).toBeNull();
  });

  it("el orden y el filtro por nota viajan a la API y el encabezado cuenta lo filtrado", async () => {
    render(<ReviewsSection {...props} />, { locale: "en" });
    await screen.findByText("@lucia.cine");

    fireEvent.change(screen.getByRole("combobox", { name: "Sort" }), {
      target: { value: "lowest" },
    });
    await waitFor(() => expect(estado.llamadas.at(-1)).toContain("orden=nota-asc"));
    fireEvent.change(screen.getByRole("combobox", { name: "Rating" }), { target: { value: "9" } });

    expect(await screen.findByRole("heading", { name: "Showing 1 of 3" })).toBeInTheDocument();
    expect(estado.llamadas.at(-1)).toContain("nota_min=9");

    fireEvent.change(screen.getByRole("combobox", { name: "Rating" }), {
      target: { value: "lt5" },
    });
    await waitFor(() => expect(estado.llamadas.at(-1)).toContain("nota_max=4"));

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(
      await screen.findByRole("heading", { name: "From the community (3)" })
    ).toBeInTheDocument();
  });

  it("si el texto recortado se corta, ofrece «Read more» y lo despliega", async () => {
    // jsdom no calcula alturas: se simula un contenido más alto que lo visible.
    vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(120);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(72);
    render(<ReviewsSection {...props} />, { locale: "en" });
    const larga = await screen.findByText(LARGA);

    expect(larga).toHaveClass("line-clamp-3");
    fireEvent.click((await screen.findAllByRole("button", { name: "Read more" }))[0]);
    expect(larga).not.toHaveClass("line-clamp-3");
    expect(screen.getByRole("button", { name: "Read less" })).toBeInTheDocument();
  });

  it("si el texto entra entero, no hay «Read more»", async () => {
    vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(72);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(72);
    render(<ReviewsSection {...props} />, { locale: "en" });

    await screen.findByText(LARGA);
    expect(screen.queryByRole("button", { name: "Read more" })).toBeNull();
  });

  it("si la lista falla, avisa y «Try again» la vuelve a pedir", async () => {
    // Q-03: todo error de carga se puede reintentar (antes era solo un texto).
    estado.fallas = 1;
    render(<ReviewsSection {...props} />, { locale: "en" });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Try again later."
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("@lucia.cine")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(estado.llamadas.filter((l) => l.startsWith("GET /api/reviews/?"))).toHaveLength(2);
  });

  it("sin reseñas lo dice", async () => {
    estado.vacia = true;
    render(<ReviewsSection {...props} />, { locale: "en" });

    expect(
      await screen.findByText("No reviews yet. Be the first to write one.")
    ).toBeInTheDocument();
  });
});

describe("tu reseña", () => {
  const mia = {
    id: 9,
    valor: 9,
    texto: "La vi tres veces.",
    fecha: "2026-10-01",
    moderada: false,
  };

  it("aparece arriba con Editar y Borrar, y borrar deja la nota", async () => {
    estado.perfil = { nombre: "Juan", apellido: "Pérez", avatar_id: 1 };
    const onEditar = vi.fn();
    const onTextoBorrado = vi.fn();
    render(
      <ReviewsSection {...props} mia={mia} onEditar={onEditar} onTextoBorrado={onTextoBorrado} />,
      {
        locale: "en",
      }
    );

    const tuya = screen.getByRole("article", { name: "Your review" });
    expect(within(tuya).getByText("La vi tres veces.")).toBeInTheDocument();
    fireEvent.click(within(tuya).getByRole("button", { name: "Edit" }));
    expect(onEditar).toHaveBeenCalled();

    fireEvent.click(within(tuya).getByRole("button", { name: "Delete review" }));
    const confirmar = await screen.findByRole("alertdialog", { name: "Delete review?" });
    fireEvent.click(within(confirmar).getByRole("button", { name: "Delete review" }));

    await waitFor(() => expect(onTextoBorrado).toHaveBeenCalled());
    expect(estado.llamadas).toContain("DELETE /api/reviews/9/texto/");
    expect(toast.success).toHaveBeenCalledWith("Review deleted.");
  });

  it("moderada: Borrar queda inerte y se explica por qué", async () => {
    estado.perfil = { nombre: "Juan", apellido: "Pérez", avatar_id: 1 };
    render(<ReviewsSection {...props} mia={{ ...mia, moderada: true }} />, { locale: "en" });

    const tuya = screen.getByRole("article", { name: "Your review" });
    expect(
      within(tuya).getByText("This review was moderated, so you can’t edit or delete its text.")
    ).toBeVisible();
    const borrar = within(tuya).getByRole("button", { name: "Delete review" });
    expect(borrar).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(borrar);
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(estado.llamadas).not.toContain("DELETE /api/reviews/9/texto/");
  });

  it("sin texto no hay tarjeta propia", async () => {
    estado.perfil = { nombre: "Juan", apellido: "Pérez", avatar_id: 1 };
    render(<ReviewsSection {...props} mia={{ ...mia, texto: null }} />, { locale: "en" });

    await screen.findByText("@lucia.cine");
    expect(screen.queryByRole("article", { name: "Your review" })).toBeNull();
  });
});

describe("reseñas de cuentas dadas de baja (26/10/2026)", () => {
  it("se muestran sin identidad, con «Usuario dado de baja»", async () => {
    estado.conBaja = true;
    render(<ReviewsSection {...props} />, { locale: "es" });

    const texto = await screen.findByText("Still my favourite.");
    const tarjeta = texto.closest("article") as HTMLElement;
    expect(within(tarjeta).getByText("Usuario dado de baja")).toBeInTheDocument();
    expect(within(tarjeta).queryByText(/^@/)).toBeNull();
    // Las demás siguen con su nombre.
    expect(screen.getByText("@lucia.cine")).toBeInTheDocument();
  });
});
