import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HomeView } from "@/components/features/HomeView";
import type { TmdbItem } from "@/lib/catalog";
import { limpiarCacheCatalogo } from "@/lib/use-catalog";
import { fireEvent, render, screen, waitFor, within } from "./render";

const estado = vi.hoisted(() => ({
  perfil: null as null | Record<string, unknown>,
  params: new URLSearchParams(),
  fallan: [] as string[],
  llamadas: [] as string[],
}));
const router = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }));
const toast = vi.hoisted(() => ({ error: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/home",
  useSearchParams: () => estado.params,
}));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => ({ perfil: estado.perfil, cargando: false }),
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
  estado.params = new URLSearchParams();
  estado.fallan = [];
  estado.llamadas = [];
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

    const hero = await screen.findByRole("heading", { level: 1 });
    expect(hero).toHaveTextContent("Insidious: Out of the Further");
    const seccionHero = hero.closest("section") as HTMLElement;
    expect(within(seccionHero).getByText("#1 trending")).toBeInTheDocument();
    expect(within(seccionHero).getByText("Horror, Thriller")).toBeInTheDocument();
    expect(within(seccionHero).getByRole("link", { name: /View details/ })).toHaveAttribute(
      "href",
      "/movie/1291595"
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

  it("suma Recomendado con sus géneros y el botón Ask FilmAI", async () => {
    render(<HomeView />, { locale: "en" });

    const recomendado = await fila("Recommended for you");
    expect(
      within(recomendado).getByText("Based on your high ratings in Thriller, Drama, and Crime")
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ask FilmAI" })).toHaveAttribute("href", "/chat");
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

describe("selector de tipo", () => {
  it("con ?type=movie cambia el Hero, la fuente de las filas y la descripción", async () => {
    estado.params = new URLSearchParams("type=movie");
    render(<HomeView />, { locale: "en" });

    const hero = await screen.findByRole("heading", { level: 1 });
    // Insidious es el Hero de All, así que Movies muestra el siguiente.
    expect(hero).toHaveTextContent("Fall 2: Deadpoint");
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
