"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { MediaCard } from "@/components/features/MediaCard";
import { TypeSelector, type ContentType } from "@/components/features/TypeSelector";
import { ApiError } from "@/lib/api";
import { normalizeTitles, type TmdbItem } from "@/lib/catalog";
import { translateError } from "@/lib/errors";
import { useFormats } from "@/lib/format";
import { routes } from "@/lib/routes";
import {
  MAX_TEXTO,
  NOTAS,
  aniosDisponibles,
  busquedaDesdeUrl,
  consultaApi,
  filtrosActivos,
  urlDeBusqueda,
  type Busqueda,
  type Nota,
} from "@/lib/search";
import { useCatalog } from "@/lib/use-catalog";

type Pagina = { page: number; total_pages: number; total_results: number; results: TmdbItem[] };
type Generos = { genres: { id: number; name: string }[] };

/** Espera después de la última tecla antes de buscar (doc 04 §5b). */
const ESPERA_MS = 350;
/** Géneros con el mismo id en películas y series: sobreviven a cambiar el tipo. */
const GENEROS_COMUNES = new Set([16, 18, 35, 37, 80, 99, 9648, 10751]);
/** Géneros solo de series que TMDB no traduce (también llegan en inglés en `es-MX`). */
const SIN_TRADUCCION: Record<number, "kids" | "news" | "reality" | "soap" | "talk"> = {
  10762: "kids",
  10763: "news",
  10764: "reality",
  10766: "soap",
  10767: "talk",
};
const ETIQUETA_NOTA = {
  "9": "ratingAtLeastNine",
  "8": "ratingAtLeastEight",
  "7": "ratingAtLeastSeven",
  "6": "ratingAtLeastSix",
  "5": "ratingAtLeastFive",
  lt5: "ratingBelowFive",
} as const;

function mensaje(error: unknown) {
  return error instanceof ApiError ? error.message : translateError({ code: "unknown" });
}

/**
 * Buscar (C-06), según el canvas. La búsqueda vive en la URL; cambiarla usa la
 * History API como el selector del Home, así no se vuelve a pedir la página al
 * servidor y «Atrás» sale de Buscar. Los datos los arma `GET /api/catalogo/browse/`.
 */
export function SearchView() {
  const t = useTranslations();
  const router = useRouter();
  const formats = useFormats();
  const busqueda = busquedaDesdeUrl(useSearchParams());
  const [texto, setTexto] = useState(busqueda.q);
  const [intento, setIntento] = useState(0);
  const campo = useRef<HTMLInputElement>(null);
  const resultados = useCatalog<Pagina>(consultaApi(busqueda), intento);
  const generos = useCatalog<Generos>(`/api/catalogo/genres/?tipo=${busqueda.tipo}`, intento);

  function cambiar(cambios: Partial<Busqueda>) {
    // Cualquier cambio vuelve a la página 1, salvo que el cambio sea la página.
    const nueva = { ...busqueda, pagina: 1, ...cambios };
    window.history.replaceState(null, "", urlDeBusqueda(nueva));
  }

  // El texto se aplica 350 ms después de la última tecla.
  useEffect(() => {
    if (texto === busqueda.q) return;
    const espera = window.setTimeout(() => cambiar({ q: texto }), ESPERA_MS);
    return () => window.clearTimeout(espera);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo el texto dispara la espera
  }, [texto]);

  // En escritorio el campo toma el foco; en celular el teclado taparía los resultados.
  useEffect(() => {
    if (window.matchMedia?.("(min-width: 768px)").matches) campo.current?.focus();
  }, []);

  function cerrar() {
    // Si el documento se cargó en otra página, se llegó navegando dentro de la
    // app: se vuelve ahí. Si se abrió directo en /search, se va al Inicio.
    const [entrada] = performance.getEntriesByType("navigation");
    const inicio = entrada ? new URL(entrada.name).pathname : routes.search;
    if (inicio !== routes.search) router.back();
    else router.push(routes.explore);
  }

  useEffect(() => {
    function alApretar(evento: KeyboardEvent) {
      // Con un diálogo abierto, Escape lo cierra a él (lo maneja `<dialog>`).
      if (evento.key !== "Escape" || document.querySelector("dialog[open]")) return;
      evento.preventDefault();
      cerrar();
    }
    document.addEventListener("keydown", alApretar);
    return () => document.removeEventListener("keydown", alApretar);
  });

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (texto !== busqueda.q) cambiar({ q: texto });
  }

  function borrarTexto() {
    setTexto("");
    cambiar({ q: "" });
    campo.current?.focus();
  }

  function elegirTipo(tipo: ContentType) {
    // Los ids de género difieren por tipo salvo 8: los demás no se arrastran.
    const genero =
      busqueda.genero !== null && GENEROS_COMUNES.has(busqueda.genero) ? busqueda.genero : null;
    cambiar({ tipo, genero });
  }

  function limpiar() {
    if (filtrosActivos(busqueda) > 0) {
      cambiar({ genero: null, anio: null, nota: null });
    } else {
      borrarTexto();
    }
  }

  function irAPagina(pagina: number) {
    cambiar({ pagina });
    window.scrollTo({ top: 0 });
  }

  const titulos = normalizeTitles(resultados.data?.results ?? []);
  const pagina = resultados.data;
  const q = busqueda.q.trim();
  const conCriterio = q !== "" || filtrosActivos(busqueda) > 0;
  const etiquetaGenero = (genero: { id: number; name: string }) =>
    SIN_TRADUCCION[genero.id] ? t(`search.genres.${SIN_TRADUCCION[genero.id]}`) : genero.name;

  const pildora =
    "inline-flex h-12 items-center gap-2.5 rounded-[10px] pr-1.5 pl-3.5 text-sm whitespace-nowrap text-fg-3 shadow-[inset_0_0_0_1px_var(--line)]";
  const selector =
    "h-10 min-w-32 cursor-pointer rounded-lg border-0 bg-raised-2 px-2 text-center text-[15px] font-semibold text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

  return (
    <main
      id="contenido"
      className="mx-auto flex max-w-[1360px] flex-col gap-4 px-5 pt-5 pb-[120px] md:gap-7 md:px-10 md:pt-6 md:pb-20"
    >
      <h1 className="mb-[15px] font-display text-[44px] leading-none md:sr-only">
        {t("nav.main.search")}
      </h1>

      <search aria-label={t("search.input.label")} className="flex flex-col gap-4 md:gap-7">
        <div className="flex items-center gap-4">
          <form onSubmit={enviar} className="relative flex-1">
            <label htmlFor="busqueda" className="sr-only">
              {t("common.search.placeholder")}
            </label>
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute top-4 left-4 size-5 text-fg-3 md:top-[23px] md:left-[22px] md:size-[26px]"
            />
            <input
              ref={campo}
              id="busqueda"
              type="search"
              enterKeyHint="search"
              autoComplete="off"
              maxLength={MAX_TEXTO}
              value={texto}
              onChange={(evento) => setTexto(evento.target.value)}
              placeholder={t("common.search.placeholder")}
              className="h-[52px] w-full rounded-xl border-0 bg-raised px-12 text-[17px] font-medium text-foreground shadow-[inset_0_0_0_1px_var(--line)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:h-[72px] md:rounded-[14px] md:px-16 md:font-display md:text-[34px] md:font-extrabold [&::-webkit-search-cancel-button]:appearance-none"
            />
            {texto && (
              <button
                type="button"
                onClick={borrarTexto}
                aria-label={t("search.input.clearLabel")}
                className="absolute top-1 right-1 grid size-11 cursor-pointer place-items-center rounded-[10px] text-fg-3 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring md:top-3.5 md:right-3.5"
              >
                <X aria-hidden="true" className="size-5" />
              </button>
            )}
          </form>
          <button
            type="button"
            onClick={cerrar}
            className="hidden h-12 cursor-pointer items-center gap-2.5 rounded-[10px] px-3.5 font-medium text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring md:inline-flex"
          >
            {t("common.actions.close")}
            <kbd className="rounded-md px-1.5 py-0.5 font-sans text-xs font-semibold text-fg-3 shadow-[inset_0_0_0_1px_var(--line)]">
              {t("search.close.shortcut")}
            </kbd>
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <TypeSelector value={busqueda.tipo} onChange={elegirTipo} className="w-full md:w-auto" />
          <div className="flex flex-wrap items-center gap-3">
            <label className={pildora}>
              {t("search.filters.genreLabel")}
              <select
                value={busqueda.genero ?? ""}
                onChange={(evento) =>
                  cambiar({ genero: evento.target.value ? Number(evento.target.value) : null })
                }
                className={selector}
              >
                <option value="">{t("search.filters.allGenres")}</option>
                {generos.data?.genres.map((genero) => (
                  <option key={genero.id} value={genero.id}>
                    {etiquetaGenero(genero)}
                  </option>
                ))}
              </select>
            </label>
            <label className={pildora}>
              {t("search.filters.yearLabel")}
              <select
                value={busqueda.anio ?? ""}
                onChange={(evento) =>
                  cambiar({ anio: evento.target.value ? Number(evento.target.value) : null })
                }
                className={selector}
              >
                <option value="">{t("search.filters.anyYear")}</option>
                {aniosDisponibles(new Date().getFullYear()).map((anio) => (
                  <option key={anio} value={anio}>
                    {anio}
                  </option>
                ))}
              </select>
            </label>
            <label className={pildora}>
              {t("common.rating.label")}
              <select
                value={busqueda.nota ?? ""}
                onChange={(evento) =>
                  cambiar({ nota: (evento.target.value || null) as Nota | null })
                }
                className={selector}
              >
                <option value="">{t("common.filters.anyRating")}</option>
                {NOTAS.map((nota) => (
                  <option key={nota} value={nota}>
                    {t(`common.filters.${ETIQUETA_NOTA[nota]}`)}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </search>

      {resultados.status === "error" ? (
        <div className="flex flex-col items-start gap-4 py-16">
          <p role="alert" className="text-fg-2">
            {mensaje(resultados.error)}
          </p>
          <button
            type="button"
            onClick={() => setIntento((anterior) => anterior + 1)}
            className="inline-flex h-12 cursor-pointer items-center rounded-lg bg-raised-2 px-[22px] font-semibold focus-visible:outline-2 focus-visible:outline-ring"
          >
            {t("common.actions.retry")}
          </button>
        </div>
      ) : resultados.status !== "ok" ? (
        <ul aria-hidden="true" className={GRILLA}>
          {Array.from({ length: 12 }, (_, i) => (
            <li key={i} className="flex flex-col gap-2.5">
              <span className="block aspect-[2/3] w-full animate-pulse rounded-lg bg-raised motion-reduce:animate-none" />
              <span className="h-4 w-3/4 animate-pulse rounded bg-raised motion-reduce:animate-none" />
            </li>
          ))}
        </ul>
      ) : titulos.length === 0 ? (
        <div
          role="status"
          className="flex max-w-[640px] flex-col items-start gap-3 pt-12 pb-20 md:gap-3.5 md:pt-24 md:pb-[120px]"
        >
          <p className="font-display text-[44px] leading-[0.95] break-words md:text-[64px]">
            {q
              ? t("search.results.emptyTitle", { query: q })
              : t("search.results.emptyFiltersTitle")}
          </p>
          <p className="text-pretty text-fg-2 md:text-[17px]">{t("search.results.emptyHint")}</p>
          {conCriterio && (
            <button
              type="button"
              onClick={limpiar}
              className="mt-2 inline-flex h-12 cursor-pointer items-center rounded-[10px] bg-raised-2 px-5 font-semibold focus-visible:outline-2 focus-visible:outline-ring"
            >
              {filtrosActivos(busqueda) > 0
                ? t("common.filters.clear")
                : t("search.input.clearLabel")}
            </button>
          )}
        </div>
      ) : (
        <>
          {conCriterio && pagina && (
            <p role="status" className="text-sm text-fg-2 md:text-[15px]">
              <span className="font-semibold text-foreground">
                {t("search.results.count", { count: pagina.total_results })}
              </span>
              {q && ` ${t("search.results.queryHint", { query: q })}`}
            </p>
          )}
          <ul className={GRILLA}>
            {titulos.map((titulo) => (
              <li key={`${titulo.tipo}-${titulo.id}`}>
                <MediaCard
                  title={titulo}
                  showType={busqueda.tipo === "all"}
                  from="search"
                  fluid
                  showUnrated
                />
              </li>
            ))}
          </ul>
          {pagina && pagina.total_pages > 1 && (
            <nav
              aria-label={t("search.pagination.label")}
              className="flex items-center justify-between gap-3 pt-3 md:justify-center md:gap-4 md:pt-4"
            >
              <button
                type="button"
                disabled={busqueda.pagina <= 1}
                onClick={() => irAPagina(busqueda.pagina - 1)}
                className="h-11 cursor-pointer rounded-[10px] px-3.5 font-medium text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-default disabled:opacity-50 md:px-4"
              >
                {t("common.pagination.previous")}
              </button>
              <span className="text-sm text-fg-2 tabular-nums md:text-[15px]">
                {t("search.pagination.position", {
                  page: formats.number(busqueda.pagina),
                  pageCount: formats.number(pagina.total_pages),
                })}
              </span>
              <button
                type="button"
                disabled={busqueda.pagina >= pagina.total_pages}
                onClick={() => irAPagina(busqueda.pagina + 1)}
                className="h-11 cursor-pointer rounded-[10px] bg-raised-2 px-4 font-semibold focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-default disabled:opacity-50 md:px-[18px]"
              >
                {t("common.pagination.next")}
              </button>
            </nav>
          )}
        </>
      )}
    </main>
  );
}

const GRILLA =
  "grid grid-cols-2 gap-x-3.5 gap-y-6 md:grid-cols-[repeat(auto-fill,minmax(min(168px,100%),1fr))] md:gap-x-5 md:gap-y-8";
