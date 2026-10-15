"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search, SlidersHorizontal, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { FiltersSheet } from "@/components/features/FiltersSheet";
import { MediaCard, MediaCardSkeleton } from "@/components/features/MediaCard";
import { TypeSelector, type ContentType } from "@/components/features/TypeSelector";
import { ErrorRetry } from "@/components/ui/ErrorRetry";
import { ApiError } from "@/lib/api";
import { normalizeTitles, type TmdbItem } from "@/lib/catalog";
import { translateError } from "@/lib/errors";
import { routes } from "@/lib/routes";
import {
  ETIQUETA_NOTA,
  MAX_TEXTO,
  NOTAS,
  opcionesDeAnio,
  anioDesdeOpcion,
  opcionDeAnio,
  busquedaDesdeUrl,
  consultaApi,
  filtrosActivos,
  guardarScrollBusqueda,
  guardarUltimaBusqueda,
  scrollGuardado,
  urlDeBusqueda,
  type Busqueda,
  type Nota,
} from "@/lib/search";
import { useCatalog, useCatalogPaginas } from "@/lib/use-catalog";

type Pagina = { page: number; total_pages: number; total_results: number; results: TmdbItem[] };
type Generos = { genres: { id: number; name: string }[] };

/**
 * Páginas que se cargan como máximo (500 resultados; 1000 en «Todo»). También
 * acota lo que dispara una URL con `page` alto: cada página es un pedido.
 */
const MAX_PAGINAS = 25;
/** Distancia al final de la grilla a la que se pide la página siguiente. */
const ANTICIPO = "600px";
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
  const busqueda = busquedaDesdeUrl(useSearchParams());
  const activos = filtrosActivos(busqueda);
  const [texto, setTexto] = useState(busqueda.q);
  const [intento, setIntento] = useState(0);
  const [hoja, setHoja] = useState(false);
  const campo = useRef<HTMLInputElement>(null);
  // Carga al bajar (pedido del usuario, 14/10/2026): `page` en la URL es cuántas
  // páginas se cargaron, así volver desde la ficha las recupera de la caché.
  const cargadas = Math.min(busqueda.pagina, MAX_PAGINAS);
  const resultados = useCatalogPaginas<Pagina>(
    Array.from({ length: cargadas }, (_, i) => consultaApi({ ...busqueda, pagina: i + 1 })),
    intento
  );
  const centinela = useRef<HTMLDivElement>(null);
  const scrollRestaurado = useRef(false);
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

  // La miga «Search» de la ficha vuelve a esta búsqueda (no a una vacía).
  const url = urlDeBusqueda(busqueda);
  useEffect(() => guardarUltimaBusqueda(url), [url]);

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
    if (activos > 0) {
      cambiar({ genero: null, anio: null, nota: null });
    } else {
      borrarTexto();
    }
  }

  const primera = resultados.paginas[0];
  // `normalizeTitles` descarta repetidos: si la popularidad cambió entre una
  // página y la siguiente, un título puede venir dos veces.
  const titulos = normalizeTitles(resultados.paginas.flatMap((pagina) => pagina.results));
  const hayMas = primera !== undefined && cargadas < Math.min(primera.total_pages, MAX_PAGINAS);
  const puedeSeguir =
    resultados.status === "ok" &&
    !resultados.cargandoMas &&
    resultados.paginas.length === cargadas &&
    hayMas;

  // Al volver de una ficha, con todas las páginas ya en pantalla (salen de la
  // caché), la grilla vuelve a donde estaba. Una sola vez por visita.
  const todasCargadas = resultados.paginas.length === cargadas;
  useEffect(() => {
    if (scrollRestaurado.current || !todasCargadas) return;
    scrollRestaurado.current = true;
    const y = scrollGuardado(url);
    // Un cuadro después: deja que Next termine su propio manejo del scroll.
    if (y !== null) requestAnimationFrame(() => window.scrollTo({ top: y }));
  }, [todasCargadas, url]);

  // Cuando el final de la grilla se acerca a la pantalla, se pide la página siguiente.
  useEffect(() => {
    const nodo = centinela.current;
    if (!nodo || !puedeSeguir || typeof IntersectionObserver === "undefined") return;
    const observador = new IntersectionObserver(
      (entradas) => {
        if (!entradas.some((entrada) => entrada.isIntersecting)) return;
        // El aviso llega asincrónico y `cambiar` recuerda la búsqueda de cuando
        // se creó el observador: si la URL ya cambió (un filtro elegido
        // mientras tanto), avanzar con la vieja lo borraría. Se compara
        // normalizada para que el orden de los parámetros no importe.
        const actual = urlDeBusqueda(busquedaDesdeUrl(new URLSearchParams(window.location.search)));
        if (actual === url) cambiar({ pagina: cargadas + 1 });
      },
      { rootMargin: `0px 0px ${ANTICIPO} 0px` }
    );
    observador.observe(nodo);
    return () => observador.disconnect();
    // `url` resume la búsqueda que usa `cambiar`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [puedeSeguir, cargadas, url]);
  const q = busqueda.q.trim();
  const conCriterio = q !== "" || activos > 0;
  const opcionesGenero = (generos.data?.genres ?? []).map((genero) => ({
    id: genero.id,
    etiqueta: SIN_TRADUCCION[genero.id]
      ? t(`search.genres.${SIN_TRADUCCION[genero.id]}`)
      : genero.name,
  }));

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
          <div className="flex w-full gap-2 md:w-auto">
            <TypeSelector value={busqueda.tipo} onChange={elegirTipo} className="flex-1" compact />
            {/* En celular los filtros van en una hoja (canvas «Search · mobile»). */}
            <button
              type="button"
              aria-haspopup="dialog"
              aria-label={t("search.filters.openLabel", { activeCount: activos })}
              onClick={() => setHoja(true)}
              className="inline-flex h-12 shrink-0 cursor-pointer items-center gap-1.5 rounded-full bg-raised px-3.5 text-sm font-semibold shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:hidden"
            >
              <SlidersHorizontal aria-hidden="true" className="size-[18px]" />
              {t("common.filters.title")}
              {activos > 0 && (
                <span
                  aria-hidden="true"
                  className="grid h-5 min-w-5 place-items-center rounded-full bg-primary px-1.5 text-xs font-bold text-primary-foreground"
                >
                  {activos}
                </span>
              )}
            </button>
          </div>
          <div className="hidden flex-wrap items-center gap-3 md:flex">
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
                {opcionesGenero.map((genero) => (
                  <option key={genero.id} value={genero.id}>
                    {genero.etiqueta}
                  </option>
                ))}
              </select>
            </label>
            <label className={pildora}>
              {t("search.filters.yearLabel")}
              <select
                value={opcionDeAnio(busqueda.anio)}
                onChange={(evento) => cambiar({ anio: anioDesdeOpcion(evento.target.value) })}
                className={selector}
              >
                <option value="">{t("search.filters.anyYear")}</option>
                <option value="upcoming">{t("search.filters.upcoming")}</option>
                {opcionesDeAnio(new Date().getFullYear()).map((opcion) => (
                  <option key={opcion.valor} value={opcion.valor}>
                    {opcion.decada === null
                      ? opcion.valor
                      : t("search.filters.decade", { decade: String(opcion.decada) })}
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
      {hoja && (
        <FiltersSheet
          busqueda={busqueda}
          generos={opcionesGenero}
          onCambiar={cambiar}
          onClose={() => setHoja(false)}
        />
      )}

      {resultados.status === "error" && resultados.paginas.length === 0 ? (
        <ErrorRetry
          mensaje={mensaje(resultados.error)}
          onReintentar={() => setIntento((anterior) => anterior + 1)}
          alertaEnTexto
          className="gap-4 py-16"
        />
      ) : resultados.status === "loading" ? (
        <ul aria-hidden="true" className={GRILLA}>
          {Array.from({ length: 12 }, (_, i) => (
            <MediaCardSkeleton key={i} />
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
              {activos > 0 ? t("common.filters.clear") : t("search.input.clearLabel")}
            </button>
          )}
        </div>
      ) : (
        <>
          {conCriterio && primera && (
            <p role="status" className="text-sm text-fg-2 md:text-[15px]">
              <span className="font-semibold text-foreground">
                {t("search.results.count", { count: primera.total_results })}
              </span>
              {q && ` ${t("search.results.queryHint", { query: q })}`}
            </p>
          )}
          <ul
            aria-busy={resultados.cargandoMas}
            className={GRILLA}
            // Abrir una ficha guarda dónde estaba la grilla (ver `scrollGuardado`).
            onClickCapture={() => guardarScrollBusqueda(url, window.scrollY)}
          >
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
          {resultados.cargandoMas && (
            <ul aria-hidden="true" className={GRILLA}>
              {Array.from({ length: 6 }, (_, i) => (
                <MediaCardSkeleton key={i} />
              ))}
            </ul>
          )}
          {resultados.status === "error" && (
            <ErrorRetry
              mensaje={mensaje(resultados.error)}
              onReintentar={() => setIntento((anterior) => anterior + 1)}
              alertaEnTexto
              className="gap-4 py-6"
            />
          )}
          <div ref={centinela} aria-hidden="true" />
        </>
      )}
    </main>
  );
}

const GRILLA =
  "grid grid-cols-2 gap-x-3.5 gap-y-6 md:grid-cols-[repeat(auto-fill,minmax(min(168px,100%),1fr))] md:gap-x-5 md:gap-y-8";
