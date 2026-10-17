import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TitleView } from "@/components/features/title/TitleView";
import { limpiarCacheCatalogo } from "@/lib/use-catalog";
import { fireEvent, render, screen, waitFor, within } from "./render";

const estado = vi.hoisted(() => ({
  perfil: null as null | Record<string, unknown>,
  params: new URLSearchParams(),
  path: "/movie/157336",
  mia: null as null | Record<string, unknown>,
  fallaDetalle: false,
  detalleColgado: false,
  /** Cuántos pedidos de las listas del usuario fallan antes de responder bien. */
  fallasListas: 0,
  llamadas: [] as { path: string; method: string; body?: unknown }[],
}));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => estado.path,
  useSearchParams: () => estado.params,
}));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => ({ perfil: estado.perfil, avatares: [], cargando: false }),
}));
vi.mock("sonner", () => ({ toast }));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  // `vi.mock` corre antes que los imports del archivo: los datos se cargan acá.
  const datos = await import("./title-fixtures");
  const listas = () => [
    {
      id: 2,
      nombre: "Watched",
      clave: "vistas",
      tipo: "predeterminada",
      cantidad_items: 1,
      contiene: Boolean(estado.mia),
      item_id: estado.mia ? 70 : null,
    },
  ];
  return {
    ...real,
    apiFetch: vi.fn(async (path: string, opciones: { method?: string; body?: unknown } = {}) => {
      const method = opciones.method ?? "GET";
      estado.llamadas.push({ path, method, body: opciones.body });
      if (path === "/api/catalogo/movie/157336/") {
        if (estado.detalleColgado) return new Promise(() => {});
        if (estado.fallaDetalle)
          throw new real.ApiError(502, { code: "upstream_error", params: {}, errors: [] });
        return structuredClone(datos.INTERSTELLAR);
      }
      if (path === "/api/catalogo/movie/157336/credits/")
        return structuredClone(datos.CREDITOS_INTERSTELLAR);
      if (path === "/api/catalogo/tv/1396/") return structuredClone(datos.BREAKING_BAD);
      if (path === "/api/catalogo/tv/1396/credits/")
        return structuredClone(datos.CREDITOS_BREAKING_BAD);
      if (path.startsWith("/api/reviews/mias/")) {
        if (!estado.mia)
          throw new real.ApiError(404, { code: "not_found", params: {}, errors: [] });
        return structuredClone(estado.mia);
      }
      if (path.startsWith("/api/lists/?")) {
        if (estado.fallasListas > 0) {
          estado.fallasListas--;
          throw new real.ApiError(500, { code: "server_error", params: {}, errors: [] });
        }
        return listas();
      }
      if (path.startsWith("/api/reviews/?"))
        return { total: 0, total_comunidad: 0, next: null, previous: null, results: [] };
      if (path === "/api/lists/4/") return { id: 4, nombre: "Sci Fi", clave: null };
      // Creada con la cuenta en español: el nombre guardado no sirve para la miga.
      if (path === "/api/lists/1/") return { id: 1, nombre: "Favoritos", clave: "favoritos" };
      if (path === "/api/reviews/" && method === "POST") {
        estado.mia = { id: 9, fecha: "2026-10-14", texto: null, ...(opciones.body as object) };
        return structuredClone(estado.mia);
      }
      if (path === "/api/reviews/9/texto/") {
        estado.mia = { ...estado.mia, texto: null };
        return undefined;
      }
      if (path === "/api/reviews/9/" && method === "PUT") {
        estado.mia = { ...estado.mia, ...(opciones.body as object) };
        return structuredClone(estado.mia);
      }
      if (path === "/api/reviews/9/" && method === "DELETE") {
        estado.mia = null;
        return undefined;
      }
      throw new Error(`Sin respuesta simulada para ${method} ${path}`);
    }),
  };
});

beforeEach(() => {
  estado.perfil = null;
  estado.params = new URLSearchParams();
  estado.path = "/movie/157336";
  estado.mia = null;
  estado.fallaDetalle = false;
  estado.detalleColgado = false;
  estado.fallasListas = 0;
  estado.llamadas = [];
  limpiarCacheCatalogo();
});
afterEach(() => vi.clearAllMocks());

const pedidas = (prefijo: string, method = "GET") =>
  estado.llamadas.filter((l) => l.path.startsWith(prefijo) && l.method === method);

describe("ficha sin sesión", () => {
  it("muestra los datos, la miga, los créditos y la invitación a ingresar", async () => {
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Interstellar");
    // La pestaña dice qué ficha es (Q-01, 16/10/2026).
    // Se asigna en un efecto, después del encabezado: hay que esperarlo.
    await waitFor(() => expect(document.title).toBe("Interstellar | FilmAI"));
    expect(
      screen.getByText("Mankind was born on Earth. It was never meant to die here.")
    ).toBeInTheDocument();
    expect(screen.getByText("2h 49m")).toBeInTheDocument();
    expect(
      within(screen.getByRole("list", { name: "Genres" })).getAllByRole("listitem")
    ).toHaveLength(3);
    const miga = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(miga).getByRole("link", { name: "Home" })).toHaveAttribute("href", "/home");
    expect(screen.getByRole("link", { name: "Log in to rate or save" })).toHaveAttribute(
      "href",
      "/login?next=%2Fmovie%2F157336"
    );
    expect(await screen.findByText("Christopher Nolan")).toBeInTheDocument();
    expect(screen.getByText("Cooper")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rate" })).toBeNull();
    expect(pedidas("/api/reviews/mias/")).toHaveLength(0);
  });

  it("una serie muestra temporadas, episodios y a sus creadores", async () => {
    estado.path = "/tv/1396";
    render(<TitleView tipo="tv" id={1396} />, { locale: "en" });

    expect(await screen.findByText("5 seasons")).toBeInTheDocument();
    expect(screen.getByText("62 episodes")).toBeInTheDocument();
    expect(await screen.findByText("Created by")).toBeInTheDocument();
    expect(screen.getByText("Vince Gilligan")).toBeInTheDocument();
  });

  it("si el detalle falla, muestra el error y Reintentar vuelve a pedir", async () => {
    estado.fallaDetalle = true;
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    expect(await screen.findByRole("alert")).toHaveTextContent("The catalog couldn’t respond.");
    estado.fallaDetalle = false;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Interstellar");
  });
});

describe("ficha con sesión", () => {
  beforeEach(() => {
    // Forma de `/api/profile/`: el avatar arma las iniciales con nombre y apellido.
    estado.perfil = { nombre: "Juan", apellido: "Pérez", avatar_id: 1 };
  });

  it("mientras carga el detalle muestra el esqueleto y no invita a ingresar", async () => {
    estado.detalleColgado = true;
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    // Las listas y la calificación propia llegan antes que el detalle.
    await waitFor(() => expect(pedidas("/api/lists/?")).toHaveLength(1));
    await waitFor(() => expect(screen.getByRole("main")).toHaveAttribute("aria-busy", "true"));
    expect(screen.queryByRole("link", { name: "Log in to rate or save" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Rate" })).toBeNull();
  });

  it("viniendo de Buscar, la miga vuelve a la última búsqueda", async () => {
    window.sessionStorage.setItem("filmai:ultima-busqueda", "/search?q=interstellar");
    estado.params = new URLSearchParams("from=search");
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    const miga = screen.getByRole("navigation", { name: "Breadcrumb" });
    await waitFor(() =>
      expect(within(miga).getByRole("link", { name: "Search" })).toHaveAttribute(
        "href",
        "/search?q=interstellar"
      )
    );
    window.sessionStorage.clear();
  });

  it("viniendo de una lista, la miga la nombra", async () => {
    estado.params = new URLSearchParams("from=list-4");
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    const miga = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(miga).getByRole("link", { name: "Lists" })).toHaveAttribute("href", "/lists");
    expect(await within(miga).findByRole("link", { name: "Sci Fi" })).toHaveAttribute(
      "href",
      "/lists/4"
    );
  });

  it("viniendo de una lista predeterminada, la nombra en el idioma de la interfaz", async () => {
    estado.params = new URLSearchParams("from=list-1");
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    const miga = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(await within(miga).findByRole("link", { name: "Favorites" })).toHaveAttribute(
      "href",
      "/lists/1"
    );
  });

  it("si las listas no cargan, lo avisa y «Try again» trae los botones de las listas", async () => {
    // Q-03: antes los tres botones desaparecían sin explicación.
    estado.fallasListas = 1;
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    expect(await screen.findByText("We couldn’t load your lists. Try again.")).toHaveAttribute(
      "role",
      "alert"
    );
    expect(screen.queryByRole("button", { name: "Watched" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    // Los datos de prueba solo traen Vistas (y una personalizada).
    expect(await screen.findByRole("button", { name: "Watched" })).toBeInTheDocument();
    expect(screen.queryByText("We couldn’t load your lists. Try again.")).not.toBeInTheDocument();
  });

  it("si las listas cargan en otra ficha, el aviso de la anterior se va", async () => {
    // Misma instancia con otro título: el error de la ficha anterior no queda colgado.
    estado.fallasListas = 1;
    const { rerender } = render(<TitleView tipo="movie" id={157336} />, { locale: "en" });
    expect(await screen.findByText("We couldn’t load your lists. Try again.")).toBeInTheDocument();

    rerender(<TitleView tipo="tv" id={1396} />);

    expect(await screen.findByRole("button", { name: "Watched" })).toBeInTheDocument();
    expect(screen.queryByText("We couldn’t load your lists. Try again.")).not.toBeInTheDocument();
  });

  it("calificar publica la nota, avisa y recarga las listas", async () => {
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    fireEvent.click(await screen.findByRole("button", { name: "Rate" }));
    const dialogo = screen.getByRole("dialog", { name: "Rate Interstellar" });
    expect(
      within(dialogo).getByText("Rating Interstellar also adds it to Watched.")
    ).toBeInTheDocument();
    fireEvent.click(within(dialogo).getByRole("radio", { name: "8 out of 10" }));
    fireEvent.click(within(dialogo).getByRole("button", { name: "Post" }));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Rating posted."));
    expect(pedidas("/api/reviews/", "POST")[0].body).toEqual({
      id_tmdb: 157336,
      tipo: "movie",
      valor: 8,
    });
    expect(
      await screen.findByRole("button", { name: "Your rating: 8 out of 10. Edit" })
    ).toBeInTheDocument();
    expect(pedidas("/api/lists/?").length).toBeGreaterThanOrEqual(2);
  });

  it("vaciar el texto al editar lo borra aparte y actualiza la nota", async () => {
    estado.mia = { id: 9, valor: 9, texto: "La vi tres veces.", fecha: "2026-10-01" };
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    fireEvent.click(await screen.findByRole("button", { name: "Your rating: 9 out of 10. Edit" }));
    const dialogo = screen.getByRole("dialog", { name: "Edit rating" });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: /Review/ }), {
      target: { value: "" },
    });
    fireEvent.click(within(dialogo).getByRole("radio", { name: "7 out of 10" }));
    fireEvent.click(within(dialogo).getByRole("button", { name: "Update" }));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Rating and review updated."));
    expect(pedidas("/api/reviews/9/texto/", "DELETE")).toHaveLength(1);
    expect(pedidas("/api/reviews/9/", "PUT")[0].body).toEqual({ valor: 7 });
  });

  it("quitar la calificación pide confirmar y vuelve a «Rate»", async () => {
    estado.mia = { id: 9, valor: 9, texto: "La vi tres veces.", fecha: "2026-10-01" };
    render(<TitleView tipo="movie" id={157336} />, { locale: "en" });

    fireEvent.click(await screen.findByRole("button", { name: "Your rating: 9 out of 10. Edit" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove rating" }));
    const confirmar = await screen.findByRole("alertdialog", { name: "Remove your rating?" });
    expect(within(confirmar).getByText("La vi tres veces.")).toBeInTheDocument();
    fireEvent.click(within(confirmar).getByRole("button", { name: "Remove rating" }));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Rating and review removed."));
    expect(await screen.findByRole("button", { name: "Rate" })).toBeInTheDocument();
  });
});
