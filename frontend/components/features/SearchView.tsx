"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type FocusEvent,
  type FormEvent,
  type KeyboardEvent as TeclaDeReact,
} from "react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { Search, SlidersHorizontal, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { CAMPO_BUSQUEDA } from "@/components/campo-busqueda";
import { SugerenciasLista } from "@/components/SugerenciasLista";
import { FiltersSheet } from "@/components/features/FiltersSheet";
import { MediaCard, MediaCardSkeleton } from "@/components/features/MediaCard";
import { TypeSelector, type ContentType } from "@/components/features/TypeSelector";
import { ErrorRetry } from "@/components/ui/ErrorRetry";
import { ApiError } from "@/lib/api";
import { normalizeTitles, tmdbImage, tmdbLoader, type TmdbItem } from "@/lib/catalog";
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
  type RolPersona,
} from "@/lib/search";
import {
  esAtajoDeBusqueda,
  filasDeSugerencias,
  generoDe,
  idDe,
  moverActiva,
  personaQueCoincide,
  type Fila,
} from "@/lib/sugerencias";
import { useSentinel, ANTICIPO } from "@/lib/use-sentinel";
import { useSugerencias } from "@/lib/use-sugerencias";
import { useCatalog, useCatalogPaginas } from "@/lib/use-catalog";

/** La persona del filtro, como la devuelve `explore/` (el nombre sale de TMDB, no de la URL). */
type PersonaFiltrada = {
  id: number;
  name: string;
  rol: RolPersona | null;
  gender: number | null;
  profile_path: string | null;
};
type Pagina = {
  page: number;
  total_pages: number;
  total_results: number;
  results: TmdbItem[];
  persona?: PersonaFiltrada;
};
type Generos = { genres: { id: number; name: string }[] };

/**
 * Páginas que se cargan como máximo (500 resultados; 1000 en «Todo»). También
 * acota lo que dispara una URL con `page` alto: cada página es un pedido.
 */
const MAX_PAGINAS = 25;
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
 * servidor y «Atrás» sale de Buscar. Los datos los arma `GET /api/catalogo/explore/`.
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
  const formulario = useRef<HTMLFormElement>(null);
  const listaId = useId();
  // Sugerencias del campo (14/11/2026): las mismas que la lupa de la navbar.
  // Con la lista cerrada el hook igual trabaja: el aviso «¿Buscabas a…?» usa su respuesta.
  const [listaAbierta, setListaAbierta] = useState(false);
  const [activoId, setActivoId] = useState<string | null>(null);
  const { sugerencias, deTexto, cargando, anuncio } = useSugerencias(texto, true);
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

  // El último `q` que se aplicó a la URL. `busqueda.q` llega con un render de
  // atraso (la URL cambia con la History API), y la espera de abajo no puede
  // fiarse de ese valor viejo: al elegir una persona se borra el texto, y si
  // la espera creyera que `q` sigue siendo «ryan», volvería a escribir la URL
  // con la búsqueda anterior y borraría el filtro recién puesto.
  const qAplicada = useRef(busqueda.q);
  useEffect(() => {
    qAplicada.current = busqueda.q;
  }, [busqueda.q]);

  function cambiar(cambios: Partial<Busqueda>) {
    // Cualquier cambio vuelve a la página 1, salvo que el cambio sea la página.
    const nueva = { ...busqueda, pagina: 1, ...cambios };
    if (cambios.q !== undefined) qAplicada.current = cambios.q;
    window.history.replaceState(null, "", urlDeBusqueda(nueva));
  }

  // El texto se aplica 350 ms después de la última tecla.
  useEffect(() => {
    if (texto === qAplicada.current) return;
    const espera = window.setTimeout(() => {
      if (texto !== qAplicada.current) cambiar({ q: texto });
    }, ESPERA_MS);
    return () => window.clearTimeout(espera);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo el texto dispara la espera
  }, [texto]);

  // La miga «Search» de la ficha vuelve a esta búsqueda (no a una vacía).
  const url = urlDeBusqueda(busqueda);
  useEffect(() => guardarUltimaBusqueda(url), [url]);

  // En escritorio el campo toma el foco; en celular el teclado taparía los resultados.
  useEffect(() => {
    if (window.matchMedia?.("(min-width: 48rem)").matches) campo.current?.focus();
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
      // «/» enfoca el campo de la página (en el resto de las pantallas abre la lupa de la navbar).
      if (esAtajoDeBusqueda(evento)) {
        evento.preventDefault();
        campo.current?.focus();
        return;
      }
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
    cerrarLista();
    if (texto !== qAplicada.current) cambiar({ q: texto });
  }

  function borrarTexto() {
    setTexto("");
    cambiar({ q: "" });
    cerrarLista();
    campo.current?.focus();
  }

  function cerrarLista() {
    setListaAbierta(false);
    setActivoId(null);
  }

  const visible = listaAbierta && sugerencias !== null && sugerencias.length > 0;
  // Sin «Ver todos los resultados»: la página ya muestra todos (decisión 14/11/2026).
  const filas = filasDeSugerencias(sugerencias ?? [], false);
  const activa = visible ? filas.find((fila) => fila.id === activoId) : undefined;

  /** Una persona pone su filtro y borra el texto (juntos se combinarían); un título abre su ficha. */
  function elegir(fila: Fila) {
    const { sugerencia } = fila;
    if (sugerencia === null) return;
    cerrarLista();
    if (sugerencia.tipo === "person") {
      setTexto("");
      cambiar({ q: "", persona: sugerencia.id, rol: sugerencia.rol });
    } else {
      router.push(routes.title(sugerencia.tipo, sugerencia.id, "search"));
    }
  }

  function alApretarEnElCampo(evento: TeclaDeReact<HTMLInputElement>) {
    switch (evento.key) {
      case "ArrowDown":
        evento.preventDefault();
        if (!visible) {
          // Con la lista cerrada, ↓ (o Alt+↓) la vuelve a abrir con la última respuesta.
          if (sugerencias !== null) setListaAbierta(true);
        } else if (!evento.altKey) setActivoId(moverActiva(filas, activoId, 1));
        return;
      case "ArrowUp":
        if (!visible) return;
        evento.preventDefault();
        setActivoId(moverActiva(filas, activoId, -1));
        return;
      case "Enter":
        // Con una opción activa, Enter la elige. Sin ninguna, Enter sigue
        // buscando el texto en los títulos (el `submit` del formulario): un
        // título llamado «Nolan» tiene que poder buscarse.
        if (activa) {
          evento.preventDefault();
          elegir(activa);
        } else cerrarLista();
        return;
      case "Escape":
        // Con la lista abierta, Escape solo la cierra; si no, sigue hasta el
        // atajo de la página, que sale de Buscar.
        if (!visible) return;
        evento.preventDefault();
        evento.stopPropagation();
        cerrarLista();
        return;
      case "Tab":
        cerrarLista();
        return;
    }
  }

  function alSalirElFoco(evento: FocusEvent<HTMLFormElement>) {
    // Pasar el foco a la ✕ (dentro del mismo formulario) no es salir.
    if (formulario.current?.contains(evento.relatedTarget as Node | null)) return;
    cerrarLista();
  }

  function elegirTipo(tipo: ContentType) {
    // Los ids de género difieren por tipo salvo 8: los demás no se arrastran.
    const genero =
      busqueda.genero !== null && GENEROS_COMUNES.has(busqueda.genero) ? busqueda.genero : null;
    cambiar({ tipo, genero });
  }

  function limpiar() {
    if (activos > 0) {
      cambiar({ genero: null, anio: null, nota: null, persona: null, rol: null });
    } else {
      borrarTexto();
    }
  }

  const primera = resultados.paginas[0];
  const persona = busqueda.persona !== null ? primera?.persona : undefined;
  const personaInexistente =
    resultados.error instanceof ApiError && resultados.error.code === "person_not_found";
  // `normalizeTitles` descarta repetidos: si la popularidad cambió entre una
  // página y la siguiente, un título puede venir dos veces.
  const titulos = normalizeTitles(resultados.paginas.flatMap((pagina) => pagina.results));
  const hayMas = primera !== undefined && cargadas < Math.min(primera.total_pages, MAX_PAGINAS);
  const mostrandoResultados =
    resultados.status !== "loading" &&
    !(resultados.status === "error" && resultados.paginas.length === 0);
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
  useSentinel(centinela, {
    activo: puedeSeguir,
    margen: `0px 0px ${ANTICIPO} 0px`,
    // Recrear el observador al cambiar la página o la URL: avisa una vez al
    // empezar a observar, y si el final sigue a la vista pide la siguiente.
    reiniciar: `${cargadas} ${url}`,
    alVer: () => {
      // El aviso llega asincrónico: si la URL ya cambió (un filtro elegido
      // mientras tanto), avanzar con la vieja lo borraría. Se compara
      // normalizada para que el orden de los parámetros no importe.
      const actual = urlDeBusqueda(busquedaDesdeUrl(new URLSearchParams(window.location.search)));
      if (actual === url) cambiar({ pagina: cargadas + 1 });
    },
  });
  const q = busqueda.q.trim();
  // «¿Buscabas a…?»: con texto y sin persona filtrada, si entre las sugerencias
  // de ese mismo texto hay una persona que lo contiene, se ofrece su filmografía.
  // `deTexto === q` evita usar la respuesta de un texto que ya no es el buscado.
  const aviso =
    q !== "" && busqueda.persona === null && sugerencias !== null && deTexto === q
      ? personaQueCoincide(sugerencias, q)
      : undefined;
  // Sin texto, el contador nombra a la persona: «12 results for “Christopher Nolan”».
  const sujeto = q || persona?.name || "";
  const conCriterio = q !== "" || activos > 0;
  const opcionesGenero = (generos.data?.genres ?? []).map((genero) => ({
    id: genero.id,
    etiqueta: SIN_TRADUCCION[genero.id]
      ? t(`search.genres.${SIN_TRADUCCION[genero.id]}`)
      : genero.name,
  }));

  const pildora =
    "inline-flex h-12 items-center gap-2.5 rounded-[0.625rem] pr-1.5 pl-3.5 text-sm whitespace-nowrap text-fg-3 shadow-[inset_0_0_0_1px_var(--line)]";
  const selector =
    "h-10 min-w-32 cursor-pointer rounded-lg border-0 bg-raised-2 px-2 text-center text-[0.9375rem] font-semibold text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

  return (
    <main
      id="contenido"
      className="page-container flex flex-col gap-4 pt-5 pb-[7.5rem] md:gap-7 md:pt-6 md:pb-20"
    >
      <h1 className="mb-[0.9375rem] font-display text-[2.75rem] leading-none md:sr-only">
        {t("nav.main.explore")}
      </h1>

      <search aria-label={t("search.input.label")} className="flex flex-col gap-4 md:gap-7">
        <div className="flex items-center gap-4">
          <form
            ref={formulario}
            onSubmit={enviar}
            onBlur={alSalirElFoco}
            className="relative flex-1"
          >
            <label htmlFor="busqueda" className="sr-only">
              {t("common.search.placeholder")}
            </label>
            {/* Mismo campo que la lupa de la navbar (`campo-busqueda.ts`). */}
            <div className={CAMPO_BUSQUEDA.pildora}>
              <Search aria-hidden="true" className={CAMPO_BUSQUEDA.icono} />
              <input
                ref={campo}
                id="busqueda"
                // Combobox ARIA 1.2 como el de la lupa: el foco queda siempre en
                // el campo y la opción activa se señala con `aria-activedescendant`.
                // Por eso es `text` y no `search`: el rol `combobox` lo reemplaza.
                type="text"
                role="combobox"
                enterKeyHint="search"
                autoComplete="off"
                maxLength={MAX_TEXTO}
                aria-autocomplete="list"
                aria-expanded={visible}
                aria-controls={listaId}
                aria-activedescendant={activa?.id}
                value={texto}
                onChange={(evento) => {
                  setTexto(evento.target.value);
                  setListaAbierta(true);
                }}
                onKeyDown={alApretarEnElCampo}
                placeholder={t("common.search.placeholder")}
                className={CAMPO_BUSQUEDA.input}
              />
              {texto && (
                <button
                  type="button"
                  onClick={borrarTexto}
                  aria-label={t("search.input.clearLabel")}
                  className={CAMPO_BUSQUEDA.limpiar}
                >
                  <X aria-hidden="true" className={CAMPO_BUSQUEDA.iconoLimpiar} />
                </button>
              )}
            </div>
            {visible && (
              // Bajo el campo, sobre el chip y los filtros (no los empuja).
              <SugerenciasLista
                id={listaId}
                sugerencias={sugerencias ?? []}
                cargando={cargando}
                activaId={activa?.id}
                alElegir={elegir}
                className="absolute top-full right-0 left-0 z-30 mt-2"
              />
            )}
            <div aria-live="polite" className="sr-only">
              {anuncio}
            </div>
          </form>
          <button
            type="button"
            onClick={cerrar}
            className="hidden h-12 cursor-pointer items-center gap-2.5 rounded-[0.625rem] px-3.5 font-medium text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring md:inline-flex"
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
              <SlidersHorizontal aria-hidden="true" className="size-[1.125rem]" />
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
            {activos > 0 && (
              <button
                type="button"
                onClick={limpiar}
                className="h-11 cursor-pointer px-1.5 text-sm font-semibold text-fg-2 underline underline-offset-[3px] hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
              >
                {t("common.filters.clear")}
              </button>
            )}
          </div>
        </div>
        {persona && (
          <div className="flex">
            <span className="inline-flex min-h-11 max-w-full items-center gap-2 rounded-full bg-raised py-1 pr-1 pl-1.5 shadow-[inset_0_0_0_1px_var(--line)]">
              <FotoPersona foto={tmdbImage(persona.profile_path, "w92")} nombre={persona.name} />
              <span className="min-w-0 truncate text-[0.9375rem] font-medium">
                {persona.name}
                {persona.rol &&
                  ` · ${t("search.person.role", { role: persona.rol, gender: generoDe(persona.gender) })}`}
              </span>
              <button
                type="button"
                onClick={() => cambiar({ persona: null, rol: null })}
                aria-label={t("search.person.remove", { name: persona.name })}
                className="grid size-9 shrink-0 cursor-pointer place-items-center rounded-full text-fg-3 hover:bg-raised-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
              >
                <X aria-hidden="true" className="size-4" />
              </button>
            </span>
          </div>
        )}
      </search>
      {aviso && (
        <p className="flex min-h-11 flex-wrap items-center gap-x-2.5 gap-y-1 text-[0.9375rem] text-fg-2">
          <FotoPersona foto={aviso.foto} nombre={aviso.nombre} />
          <span>
            {t.rich("search.person.lookingFor", {
              name: aviso.nombre,
              // Un botón de verdad (no un `div` con `onClick`): se alcanza con Tab y con Enter.
              link: (texto) => (
                <button
                  type="button"
                  onClick={() => elegir({ id: idDe(aviso), sugerencia: aviso })}
                  className="inline-flex min-h-11 cursor-pointer items-center font-semibold text-primary underline underline-offset-[3px] focus-visible:outline-2 focus-visible:outline-ring"
                >
                  {texto}
                </button>
              ),
            })}
          </span>
          <span className="text-fg-3">
            · {t("search.person.role", { role: aviso.rol, gender: aviso.genero })}
          </span>
        </p>
      )}
      {hoja && (
        <FiltersSheet
          busqueda={busqueda}
          generos={opcionesGenero}
          onCambiar={cambiar}
          onClose={() => setHoja(false)}
        />
      )}

      {/* El contenedor vive siempre; el aviso se agrega después y se anuncia (un
          `role="status"` que nace con el texto no siempre se lee). Vacío sale del
          flujo con `empty:sr-only` para no sumar un hueco al flex. */}
      <div role="status" className="empty:sr-only">
        {mostrandoResultados && titulos.length === 0 && (
          <div className="flex max-w-[40rem] flex-col items-start gap-3 pt-12 pb-20 md:gap-3.5 md:pt-24 md:pb-[7.5rem]">
            <p className="font-display text-[2.75rem] leading-[0.95] break-words md:text-[4rem]">
              {q
                ? t("search.results.emptyTitle", { query: q })
                : t("search.results.emptyFiltersTitle")}
            </p>
            <p className="text-pretty text-fg-2 md:text-[1.0625rem]">
              {t("search.results.emptyHint")}
            </p>
            {conCriterio && (
              <button
                type="button"
                onClick={limpiar}
                className="mt-2 inline-flex h-12 cursor-pointer items-center rounded-[0.625rem] bg-raised-2 px-5 font-semibold focus-visible:outline-2 focus-visible:outline-ring"
              >
                {activos > 0 ? t("common.filters.clear") : t("search.input.clearLabel")}
              </button>
            )}
          </div>
        )}
        {mostrandoResultados && titulos.length > 0 && conCriterio && primera && (
          <p className="text-sm text-fg-2 md:text-[0.9375rem]">
            <span className="font-semibold text-foreground">
              {t("search.results.count", { count: primera.total_results })}
            </span>
            {sujeto && ` ${t("search.results.queryHint", { query: sujeto })}`}
          </p>
        )}
      </div>

      {personaInexistente ? (
        // TMDB no conoce a esa persona (una URL vieja o inventada): reintentar no
        // sirve, lo útil es sacar el filtro.
        <div className="flex flex-col items-start gap-4 py-16">
          <p role="alert" className="text-fg-2">
            {mensaje(resultados.error)}
          </p>
          <button
            type="button"
            onClick={limpiar}
            className="inline-flex h-12 cursor-pointer items-center rounded-[0.625rem] bg-raised-2 px-5 font-semibold focus-visible:outline-2 focus-visible:outline-ring"
          >
            {t("common.filters.clear")}
          </button>
        </div>
      ) : resultados.status === "error" && resultados.paginas.length === 0 ? (
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
      ) : titulos.length === 0 ? null : (
        <>
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

/** Foto redonda de una persona (chip y aviso); sin foto, su inicial. */
function FotoPersona({ foto, nombre }: { foto: string | null; nombre: string }) {
  return foto ? (
    <Image
      src={foto}
      alt=""
      width={32}
      height={32}
      loader={tmdbLoader}
      className="size-8 shrink-0 rounded-full object-cover"
    />
  ) : (
    <span
      aria-hidden="true"
      className="grid size-8 shrink-0 place-items-center rounded-full bg-raised-2 text-sm font-semibold text-fg-2"
    >
      {nombre.charAt(0)}
    </span>
  );
}

/** Desde md, las mismas columnas que las filas del Home (`--cols`, globals.css). */
const GRILLA =
  "grid grid-cols-2 gap-x-3.5 gap-y-6 md:grid-cols-[repeat(var(--cols),minmax(0,1fr))] md:gap-x-5 md:gap-y-8";
