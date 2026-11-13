import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HomeView } from "@/components/features/HomeView";
import type { TmdbItem } from "@/lib/catalog";
import { limpiarCacheCatalogo } from "@/lib/use-catalog";
import { fireEvent, render, screen, waitFor, within } from "./render";
import { rutasHeroPara } from "@/lib/home";
import { fall2, generosPeliculas, generosSeries, insidious, reacher } from "./catalog-fixtures";

const estado = vi.hoisted(() => ({
  perfil: null as null | Record<string, unknown>,
  cargando: false,
  sesionPosible: false,
  params: new URLSearchParams(),
  fallan: [] as string[],
  /** Prefijos que tardan un poco más en responder (o en fallar). */
  lentas: [] as string[],
  /** Todas las filas responden bien pero sin títulos. */
  vacias: false,
  llamadas: [] as string[],
  /** Lo que hay en la lista Pendientes del usuario (la más reciente primero). */
  pendientes: [] as {
    item_id: number;
    fecha_agregado: string;
    id_tmdb: number;
    tipo: "movie" | "tv";
    titulo: string;
    poster: string | null;
    anio: number | null;
    calificacion_promedio: number | null;
  }[],
}));
const router = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }));
const toast = vi.hoisted(() => ({ error: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/home",
  useSearchParams: () => estado.params,
}));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => ({
    perfil: estado.perfil,
    cargando: estado.cargando,
    sesionPosible: estado.sesionPosible,
  }),
}));
vi.mock("sonner", () => ({ toast }));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  // `vi.mock` corre antes que los imports del archivo: los datos se cargan acá.
  const { fall2, generosPeliculas, generosSeries, insidious, reacher } =
    await import("./catalog-fixtures");
  // `now-playing` y `discover` no traen media_type (verificado el 13/10/2026).
  const sinTipo = (item: TmdbItem) => ({ ...item, media_type: undefined });
  const respuestas: [string, unknown][] = [
    ["/api/catalogo/trending/?media_type=all", { results: [insidious, reacher] }],
    // TMDB sí manda media_type en trending de un solo tipo (verificado el 13/10/2026).
    [
      "/api/catalogo/trending/?media_type=movie",
      { results: [insidious, { ...fall2, media_type: "movie" }] },
    ],
    ["/api/catalogo/trending/?media_type=tv", { results: [reacher] }],
    ["/api/catalogo/now-playing/", { results: [sinTipo(fall2)] }],
    ["/api/catalogo/discover/?tipo=tv", { results: [sinTipo(reacher)] }],
    [
      "/api/catalogo/recommended/",
      { generos: ["Thriller", "Drama", "Crime"], results: [{ ...fall2, media_type: "movie" }] },
    ],
    ["/api/catalogo/genres/?tipo=movie", { genres: generosPeliculas }],
    ["/api/catalogo/genres/?tipo=tv", { genres: generosSeries }],
  ];
  return {
    ...real,
    apiFetch: vi.fn(async (path: string) => {
      estado.llamadas.push(path);
      if (estado.lentas.some((prefijo) => path.startsWith(prefijo)))
        await new Promise((resolver) => setTimeout(resolver, 60));
      // Listas del usuario (Pendientes en el Inicio). Se atienden antes que las
      // demás respuestas: `/api/lists/5/items/` también empieza con `/api/lists/`.
      if (
        path.startsWith("/api/lists/") &&
        estado.fallan.some((prefijo) => path.startsWith(prefijo))
      )
        throw new real.ApiError(500, { code: "unknown", params: {}, errors: [] });
      if (path.startsWith("/api/lists/5/items/")) {
        const clase = new URL(path, "http://x").searchParams.get("clase");
        const items = estado.pendientes.filter((item) => !clase || item.tipo === clase);
        return { next: null, total: items.length, results: items };
      }
      if (path === "/api/lists/") {
        const resumen = (id: number, clave: string, cantidad: number) => ({
          id,
          nombre: clave,
          clave,
          tipo: "predeterminada",
          cantidad_items: cantidad,
          cantidad_peliculas: 0,
          cantidad_series: 0,
          preview_posters: [],
        });
        return [
          resumen(3, "favoritos", 0),
          resumen(4, "vistas", 0),
          resumen(5, "pendientes", estado.pendientes.length),
        ];
      }
      if (estado.vacias && !path.startsWith("/api/catalogo/genres/"))
        return { results: [], generos: [] };
      if (estado.fallan.some((prefijo) => path.startsWith(prefijo)))
        throw new real.ApiError(502, { code: "upstream_error", params: {}, errors: [] });
      const respuesta = respuestas.find(([prefijo]) => path.startsWith(prefijo));
      if (!respuesta) throw new Error(`Sin respuesta simulada para ${path}`);
      return structuredClone(respuesta[1]);
    }),
  };
});

beforeEach(() => {
  estado.perfil = null;
  estado.cargando = false;
  estado.sesionPosible = false;
  estado.params = new URLSearchParams();
  estado.fallan = [];
  estado.lentas = [];
  estado.vacias = false;
  estado.llamadas = [];
  estado.pendientes = [];
  limpiarCacheCatalogo();
});
afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

const fila = (nombre: string) => screen.findByRole("region", { name: nombre });

describe("Home sin sesión", () => {
  it("muestra el Hero, Trending, New releases y la invitación a registrarse", async () => {
    render(<HomeView />, { locale: "en" });

    const hero = await screen.findByRole("heading", {
      level: 1,
      name: "Insidious: Out of the Further",
    });
    const seccionHero = hero.closest("section") as HTMLElement;
    expect(within(seccionHero).getByText("#1 trending")).toBeInTheDocument();
    expect(within(seccionHero).getByText("Horror, Thriller")).toBeInTheDocument();
    expect(within(seccionHero).getByRole("link", { name: /View details/ })).toHaveAttribute(
      "href",
      "/movie/1291595?from=home"
    );

    expect(await fila("Trending this week")).toBeInTheDocument();
    expect(await fila("New releases")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Recommended for you" })).toBeNull();
    expect(estado.llamadas.some((path) => path.includes("recommended"))).toBe(false);

    const invitacion = screen.getByRole("region", { name: "What have you watched lately?" });
    expect(within(invitacion).getByRole("link", { name: "Sign up" })).toHaveAttribute(
      "href",
      "/register"
    );
    expect(screen.queryByRole("link", { name: "Ask FilmAI" })).toBeNull();
  });
});

describe("Home con sesión", () => {
  beforeEach(() => {
    estado.perfil = { nombre: "Juan" };
  });

  it("suma Recomendado con sus géneros; el chat ya no es un link propio de la Home", async () => {
    render(<HomeView />, { locale: "en" });

    const recomendado = await fila("Recommended for you");
    expect(
      within(recomendado).getByText("Based on your high ratings in Thriller, Drama, and Crime")
    ).toBeInTheDocument();
    // El botón del chat es `ChatFab`, que vive en el layout (PR 6 del chatbot).
    expect(screen.queryByRole("link", { name: "Ask FilmAI" })).toBeNull();
    expect(screen.queryByRole("region", { name: "What have you watched lately?" })).toBeNull();
  });

  it("si una fila falla, se oculta y un solo aviso lo cuenta", async () => {
    estado.fallan = ["/api/catalogo/recommended/"];
    render(<HomeView />, { locale: "en" });

    expect(await fila("Trending this week")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Recommended for you" })).toBeNull();
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        "The catalog couldn’t respond. Try again later.",
        expect.objectContaining({ id: "home-carga" })
      )
    );
    expect(toast.error).toHaveBeenCalledTimes(1);
  });
});

const alien = {
  item_id: 11,
  fecha_agregado: "2026-11-10T12:00:00Z",
  id_tmdb: 348,
  tipo: "movie" as const,
  titulo: "Alien",
  poster: "/alien.jpg",
  anio: 1979,
  calificacion_promedio: 8.1,
};
const severance = {
  item_id: 12,
  fecha_agregado: "2026-11-09T12:00:00Z",
  id_tmdb: 95396,
  tipo: "tv" as const,
  titulo: "Severance",
  poster: "/severance.jpg",
  anio: 2022,
  calificacion_promedio: 8.4,
};

describe("fila Pendientes del Inicio (13/11/2026)", () => {
  it("sin sesión no aparece ni se piden las listas", async () => {
    estado.pendientes = [alien];
    render(<HomeView />, { locale: "en" });

    await fila("Trending this week");
    expect(screen.queryByRole("region", { name: "Watchlist" })).toBeNull();
    expect(estado.llamadas.some((path) => path.startsWith("/api/lists/"))).toBe(false);
  });

  describe("con sesión", () => {
    beforeEach(() => {
      estado.perfil = { nombre: "Juan" };
    });

    it("va después de Tendencias y antes de Estrenos, con «See all» a la lista", async () => {
      estado.pendientes = [alien, severance];
      render(<HomeView />, { locale: "en" });

      const pendientes = await fila("Watchlist");
      await fila("New releases");
      const orden = screen
        .getAllByRole("region")
        .slice(1) // la primera es el Hero
        .map((region) => region.getAttribute("aria-labelledby"))
        .map((id) => document.getElementById(id ?? "")?.textContent);
      expect(orden).toEqual([
        "Recommended for you",
        "Trending this week",
        "Watchlist",
        "New releases",
      ]);
      expect(within(pendientes).getByRole("link", { name: "See all" })).toHaveAttribute(
        "href",
        "/lists/5"
      );
      // Lo último agregado primero, y la miga de la ficha vuelve a la lista.
      const tarjetas = within(pendientes).getAllByRole("link", { name: /poster|Alien|Severance/ });
      expect(tarjetas[0]).toHaveAttribute("href", "/movie/348?from=list-5");
      expect(tarjetas[1]).toHaveAttribute("href", "/tv/95396?from=list-5");
    });

    it("con la lista vacía no aparece y no pide los ítems", async () => {
      render(<HomeView />, { locale: "en" });

      await fila("Trending this week");
      await waitFor(() => expect(estado.llamadas).toContain("/api/lists/"));
      expect(screen.queryByRole("region", { name: "Watchlist" })).toBeNull();
      expect(estado.llamadas.some((path) => path.includes("/api/lists/5/items/"))).toBe(false);
    });

    it("respeta el selector de tipo: pide solo ese tipo", async () => {
      estado.params = new URLSearchParams("type=tv");
      estado.pendientes = [alien, severance];
      render(<HomeView />, { locale: "en" });

      const pendientes = await fila("Watchlist");
      expect(estado.llamadas).toContain("/api/lists/5/items/?clase=tv");
      expect(within(pendientes).getAllByRole("listitem")).toHaveLength(1);
      expect(within(pendientes).getByText("Severance")).toBeInTheDocument();
    });

    it("si fallan todas las filas del catálogo, sigue el error con Reintentar aunque las listas respondan", async () => {
      estado.pendientes = [alien];
      estado.fallan = ["/api/catalogo/"];
      render(<HomeView />, { locale: "en" });

      expect(
        await screen.findByText("The catalog couldn’t respond. Try again later.")
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    });

    it("si fallan las listas, la fila se oculta en silencio y el resto sigue", async () => {
      estado.pendientes = [alien];
      estado.fallan = ["/api/lists/"];
      render(<HomeView />, { locale: "en" });

      expect(await fila("Trending this week")).toBeInTheDocument();
      await waitFor(() => expect(estado.llamadas).toContain("/api/lists/"));
      // Dejamos pasar un instante: si la fila fuera a aparecer, ya lo habría hecho.
      await new Promise((resolver) => setTimeout(resolver, 50));
      expect(screen.queryByRole("region", { name: "Watchlist" })).toBeNull();
      expect(toast.error).not.toHaveBeenCalled();
    });

    it("si no hay títulos de ese tipo, la fila no aparece", async () => {
      estado.params = new URLSearchParams("type=tv");
      estado.pendientes = [alien];
      render(<HomeView />, { locale: "en" });

      await fila("Trending this week");
      await waitFor(() => expect(estado.llamadas).toContain("/api/lists/5/items/?clase=tv"));
      expect(screen.queryByRole("region", { name: "Watchlist" })).toBeNull();
    });
  });
});

describe("Home mientras llega la cuenta", () => {
  // Si Recomendado apareciera recién con la cuenta, empujaría hacia abajo las
  // filas ya dibujadas (el salto de layout medido el 22/10/2026).
  it("con cookies de sesión, Recomendado ya ocupa su lugar en esqueleto", async () => {
    estado.cargando = true;
    estado.sesionPosible = true;
    render(<HomeView />, { locale: "en" });

    const recomendado = await fila("Recommended for you");
    expect(recomendado).toHaveAttribute("aria-busy", "true");
    expect(recomendado.querySelectorAll("[data-skeleton]").length).toBeGreaterThan(0);
    // Sin cuenta todavía no se pide: el esqueleto solo reserva el lugar.
    expect(estado.llamadas.some((path) => path.includes("recommended"))).toBe(false);
  });

  it("sin cookies de sesión no reserva la fila", async () => {
    estado.cargando = true;
    render(<HomeView />, { locale: "en" });

    expect(await fila("Trending this week")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Recommended for you" })).toBeNull();
  });
});

describe("selector de tipo", () => {
  it("con ?type=movie cambia el Hero, la fuente de las filas y la descripción", async () => {
    estado.params = new URLSearchParams("type=movie");
    render(<HomeView />, { locale: "en" });

    // Insidious es el Hero de All, así que Movies muestra el siguiente.
    const hero = await screen.findByRole("heading", { level: 1, name: "Fall 2: Deadpoint" });
    expect(
      within(hero.closest("section") as HTMLElement).getByText("Featured this week")
    ).toBeInTheDocument();
    const novedades = await fila("New releases");
    expect(within(novedades).getByText("In theaters now")).toBeInTheDocument();
    expect(within(novedades).getByRole("link")).not.toHaveTextContent("Movie ·");
    expect(estado.llamadas).toContain("/api/catalogo/trending/?media_type=movie");
  });

  it("elegir otra opción la guarda en la URL", async () => {
    render(<HomeView />, { locale: "en" });
    await fila("Trending this week");

    const replaceState = vi.spyOn(window.history, "replaceState");
    fireEvent.click(screen.getByRole("button", { name: "TV shows" }));

    expect(replaceState).toHaveBeenCalledWith(null, "", "/home?type=tv");
  });
});

describe("todo falla", () => {
  it("si fallan todas las filas, el error se ve una sola vez", async () => {
    // Q-03: Trending falla más tarde que las demás. Antes, mientras esperaba,
    // salía el toast de «algo no cargó» y después el mismo error en la página.
    estado.fallan = ["/api/catalogo/"];
    estado.lentas = ["/api/catalogo/trending/"];
    render(<HomeView />, { locale: "en" });

    expect(
      await screen.findByText("The catalog couldn’t respond. Try again later.")
    ).toBeInTheDocument();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("si todas las filas llegan vacías, lo dice y ofrece explorar", async () => {
    // Antes la página quedaba en blanco, sin explicación ni salida.
    estado.vacias = true;
    render(<HomeView />, { locale: "en" });

    expect(
      await screen.findByText(
        "There’s nothing to show right now. Try again later or search for something specific."
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Explore" })).toHaveAttribute("href", "/search");
  });

  it("muestra el error con Reintentar y vuelve a pedir", async () => {
    estado.fallan = ["/api/catalogo/"];
    render(<HomeView />, { locale: "en" });

    expect(
      await screen.findByText("The catalog couldn’t respond. Try again later.")
    ).toBeInTheDocument();
    estado.fallan = [];
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await fila("Trending this week")).toBeInTheDocument();
  });
});

describe("Home con el Hero pedido por el servidor (24/10/2026)", () => {
  const delServidor = {
    "/api/catalogo/trending/?media_type=all": { results: [insidious, reacher] },
    "/api/catalogo/genres/?tipo=movie": { genres: generosPeliculas },
    "/api/catalogo/genres/?tipo=tv": { genres: generosSeries },
  };

  it("el Hero está desde el primer render y no se vuelve a pedir", () => {
    render(<HomeView inicial={{ idioma: "en", datos: delServidor }} />, { locale: "en" });

    // `getBy` y no `findBy`: tiene que estar ya, sin esperar a ningún pedido.
    const hero = screen.getByRole("heading", { level: 1 });
    expect(hero).toHaveTextContent("Insidious: Out of the Further");
    expect(
      within(hero.closest("section") as HTMLElement).getByText("Horror, Thriller")
    ).toBeInTheDocument();
    expect(
      estado.llamadas.filter((path) => path.includes("trending") || path.includes("genres"))
    ).toEqual([]);
    // Las demás filas se siguen pidiendo desde el navegador.
    expect(estado.llamadas).toContain("/api/catalogo/now-playing/");
  });

  it("las rutas que pide el servidor son las mismas que busca HomeView", () => {
    // El contrato del que depende todo: si las dos listas se separan, el servidor
    // pediría datos que el navegador descarta y el Hero volvería a esperar.
    const respuestas: Record<string, unknown> = {
      "/api/catalogo/trending/?media_type=all": { results: [insidious, reacher] },
      "/api/catalogo/trending/?media_type=movie": { results: [insidious, fall2] },
      "/api/catalogo/genres/?tipo=movie": { genres: generosPeliculas },
      "/api/catalogo/genres/?tipo=tv": { genres: generosSeries },
    };
    estado.params = new URLSearchParams("type=movie");
    const datos = Object.fromEntries(
      rutasHeroPara("movie").map((ruta) => [ruta, respuestas[ruta]])
    );

    render(<HomeView inicial={{ idioma: "en", datos }} />, { locale: "en" });

    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    expect(
      estado.llamadas.filter((path) => path.includes("trending") || path.includes("genres"))
    ).toEqual([]);
  });

  it("si lo que trajo el servidor es de otro idioma, se pide de nuevo", async () => {
    render(<HomeView inicial={{ idioma: "es", datos: delServidor }} />, { locale: "en" });

    expect(
      await screen.findByRole("heading", { level: 1, name: "Insidious: Out of the Further" })
    ).toBeInTheDocument();
    expect(estado.llamadas).toContain("/api/catalogo/trending/?media_type=all");
  });

  it("sin datos del servidor se comporta como antes", async () => {
    render(<HomeView inicial={{ idioma: "en", datos: {} }} />, { locale: "en" });

    // Mientras carga no hay título del Hero, pero el Inicio nunca queda sin `<h1>`.
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Home");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Insidious: Out of the Further" })
    ).toBeInTheDocument();
    expect(estado.llamadas).toContain("/api/catalogo/trending/?media_type=all");
  });
});
