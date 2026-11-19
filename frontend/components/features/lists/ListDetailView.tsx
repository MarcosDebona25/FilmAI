"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { notFound, useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, Clock, LoaderCircle, Search, SlidersHorizontal, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount } from "@/components/AccountProvider";
import { ListActionsMenu } from "@/components/features/lists/ListActionsMenu";
import { useNombreLista } from "@/components/features/lists/ListCard";
import { ListFiltersSheet } from "@/components/features/lists/ListFiltersSheet";
import { ListNameDialog } from "@/components/features/lists/ListNameDialog";
import { useEstadoViendo } from "@/components/features/lists/use-estado-viendo";
import { WatchingCardMenu, type AccionViendo } from "@/components/features/lists/WatchingCardMenu";
import { MediaCard } from "@/components/features/MediaCard";
import { UnavailableCard } from "@/components/features/UnavailableCard";
import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { RatingDialog, mensajeDeError } from "@/components/features/title/RatingDialog";
import { ErrorRetry } from "@/components/ui/ErrorRetry";
import { ApiError, apiFetch } from "@/lib/api";
import { useFormats } from "@/lib/format";
import {
  CLASES,
  ETIQUETA_CLASE,
  ETIQUETA_ORDEN_LISTA,
  FILTROS_VACIOS,
  MAX_TEXTO,
  ORDENES_LISTA,
  combinarItems,
  consultaItems,
  esPredeterminada,
  filtrosActivos,
  filtrosDesdeUrl,
  hayFiltros,
  itemATitulo,
  rutaPaginaItems,
  urlDeFiltros,
  type FiltrosLista,
  type ItemLista,
  type PaginaItems,
  type ResumenLista,
} from "@/lib/lists";
import { crearCalificacion, editarCalificacion } from "@/lib/review-actions";
import { routes } from "@/lib/routes";
import { ETIQUETA_NOTA, NOTAS } from "@/lib/search";
import type { MiCalificacion } from "@/lib/title";
import { useCursorList } from "@/lib/use-cursor-list";
import { useSentinel } from "@/lib/use-sentinel";
import { cn } from "@/lib/utils";

/** Espera después de la última tecla antes de filtrar, como Buscar. */
const ESPERA_MS = 350;

type Datos = { items: ItemLista[]; next: string | null; total: number };
type Accion = { tipo: "quitar"; item: ItemLista };
/**
 * El diálogo de calificar abierto desde una tarjeta de Watching. `enGrilla`:
 * la tarjeta sigue ahí (menú ⋯); si no, ya pasó a Watched (el «Rate it» del
 * toast). `propia`: la calificación que ya tenía, que se edita sin mover nada.
 */
type Calificando = { item: ItemLista; enGrilla: boolean; propia: MiCalificacion | null };

/**
 * Detalle de una lista según el canvas «List detail» (L-03). Los filtros viven
 * en la URL; los ítems se piden por cursor a `GET /api/lists/{id}/items/`.
 * Watching (PR 4) usa esta misma página: suma el menú ⋯ por tarjeta, que pasa
 * el título a Watched, lo califica o lo deja sin estado, con toast y Undo.
 * Quitar de «Watched» conserva la calificación (backend, 16/11/2026).
 */
export function ListDetailView({ id }: { id: number }) {
  const t = useTranslations();
  const router = useRouter();
  const nombreDe = useNombreLista();
  const formats = useFormats();
  const { perfil, error: errorCuenta, recargar } = useAccount();
  const filtros = filtrosDesdeUrl(useSearchParams());
  const consulta = consultaItems(id, filtros);
  const [lista, setLista] = useState<ResumenLista | null>(null);
  const [noExiste, setNoExiste] = useState(false);
  const [errorLista, setErrorLista] = useState(false);
  const [texto, setTexto] = useState(filtros.q);
  // Primera página de cada combinación de filtros, y las siguientes al bajar.
  const { datos, setDatos, estado, mas, cargarMas, intento, reintentar, puedeSeguir } =
    useCursorList<PaginaItems, Datos>({
      cuenta: perfil?.pk,
      primera: consulta,
      rutaSiguiente: (next) => rutaPaginaItems(id, next),
      inicial: (pagina) => ({ items: pagina.results, next: pagina.next, total: pagina.total }),
      combinar: (actual, pagina) => ({
        ...actual,
        items: combinarItems(actual.items, pagina.results),
        next: pagina.next,
      }),
    });
  const [hoja, setHoja] = useState(false);
  const [dialogo, setDialogo] = useState<"renombrar" | "eliminar" | null>(null);
  const [accion, setAccion] = useState<Accion | null>(null);
  // Watching: qué tarjeta tiene el menú ⋯ abierto (uno solo) y qué se califica.
  const [menuAbierto, setMenuAbierto] = useState<number | null>(null);
  const [calificando, setCalificando] = useState<Calificando | null>(null);
  const [idPendientes, setIdPendientes] = useState<number | null>(null);
  const centinela = useRef<HTMLDivElement>(null);
  // Los datos de la grilla de ahora, para decidir fuera de un updater (ver `meterEnLaGrilla`).
  const datosAhora = useRef(datos);
  useEffect(() => {
    datosAhora.current = datos;
  }, [datos]);
  const titulo = useRef<HTMLHeadingElement>(null);
  const campo = useRef<HTMLInputElement>(null);
  const ids = useId();
  const activos = filtrosActivos(filtros);
  const filtrando = hayFiltros(filtros);

  // Parte de la URL de ahora y no de lo renderizado: la espera del texto y un
  // «limpiar» pueden cruzarse antes de que `useSearchParams` se entere.
  function cambiar(cambios: Partial<FiltrosLista>) {
    const actuales = filtrosDesdeUrl(new URLSearchParams(window.location.search));
    window.history.replaceState(null, "", urlDeFiltros(id, { ...actuales, ...cambios }));
  }

  function limpiar() {
    setTexto("");
    cambiar({ ...FILTROS_VACIOS, orden: filtros.orden });
  }

  // El texto se aplica 350 ms después de la última tecla.
  useEffect(() => {
    if (texto === filtros.q) return;
    const espera = window.setTimeout(() => cambiar({ q: texto }), ESPERA_MS);
    return () => window.clearTimeout(espera);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo el texto dispara la espera
  }, [texto]);

  // La lista (nombre, clave y contadores).
  useEffect(() => {
    if (!perfil?.pk) return;
    let vigente = true;
    setErrorLista(false);
    apiFetch<ResumenLista>(`/api/lists/${id}/`).then(
      (datos) => vigente && setLista(datos),
      (motivo) => {
        if (!vigente) return;
        if (motivo instanceof ApiError && motivo.status === 404) setNoExiste(true);
        else setErrorLista(true);
      }
    );
    return () => {
      vigente = false;
    };
  }, [id, perfil?.pk, intento]);

  // Carga al bajar; el botón «Cargar más» queda para teclado y como respaldo.
  // El centinela solo se dibuja cuando ya llegó la lista (con su nombre) (otro pedido,
  // que puede terminar después de la primera página): `reiniciar` hace que el
  // observador se cree cuando el nodo ya existe, y no se quede sin observar nada.
  useSentinel(centinela, {
    activo: puedeSeguir,
    alVer: cargarMas,
    reiniciar: lista ? "con-lista" : "sin-lista",
  });

  /** Saca la tarjeta y devuelve el lugar que tenía, para que Undo la ponga ahí. */
  function sacarDeLaGrilla(item: ItemLista) {
    const indice = datos?.items.findIndex((otro) => otro.item_id === item.item_id) ?? -1;
    setDatos((actual) =>
      actual
        ? {
            ...actual,
            items: actual.items.filter((otro) => otro.item_id !== item.item_id),
            total: Math.max(0, actual.total - 1),
          }
        : actual
    );
    setLista((actual) =>
      actual
        ? {
            ...actual,
            cantidad_items: Math.max(0, actual.cantidad_items - 1),
            cantidad_peliculas: Math.max(
              0,
              actual.cantidad_peliculas - (item.tipo === "movie" ? 1 : 0)
            ),
            cantidad_series: Math.max(0, actual.cantidad_series - (item.tipo === "tv" ? 1 : 0)),
          }
        : actual
    );
    // La tarjeta ya no existe: el foco va al título de la página.
    requestAnimationFrame(() => titulo.current?.focus());
    return Math.max(0, indice);
  }

  /** Vuelve una tarjeta a su lugar (Undo, o un cambio que falló). */
  function meterEnLaGrilla(item: ItemLista, indice: number) {
    // El conteo solo sube si la tarjeta de verdad se inserta. Se decide aquí, con
    // el estado de ahora, y no dentro del updater de `setDatos` (en StrictMode
    // corre dos veces).
    const actual = datosAhora.current;
    if (!actual || actual.items.some((otro) => otro.item_id === item.item_id)) return;
    const items = [...actual.items];
    items.splice(Math.min(indice, items.length), 0, item);
    datosAhora.current = { ...actual, items, total: actual.total + 1 };
    setDatos(datosAhora.current);
    setLista((anterior) =>
      anterior
        ? {
            ...anterior,
            cantidad_items: anterior.cantidad_items + 1,
            cantidad_peliculas: anterior.cantidad_peliculas + (item.tipo === "movie" ? 1 : 0),
            cantidad_series: anterior.cantidad_series + (item.tipo === "tv" ? 1 : 0),
          }
        : anterior
    );
  }

  const viendo = useEstadoViendo({
    sacar: sacarDeLaGrilla,
    meter: meterEnLaGrilla,
    onCalificar: (item) => void pedirCalificar(item, false),
  });

  async function pedirCalificar(item: ItemLista, enGrilla: boolean) {
    let propia: MiCalificacion | null = null;
    try {
      propia = await apiFetch<MiCalificacion>(
        `/api/reviews/mias/?id_tmdb=${item.id_tmdb}&tipo=${item.tipo}`
      );
    } catch (motivo) {
      if (!(motivo instanceof ApiError && motivo.status === 404)) {
        toast.error(mensajeDeError(motivo));
        return;
      }
    }
    setCalificando({ item, enGrilla, propia });
  }

  function elegirDelMenu(item: ItemLista, accion: AccionViendo) {
    setMenuAbierto(null);
    if (accion === "calificar") void pedirCalificar(item, true);
    else void viendo.mover(item, accion === "terminar" ? "vistas" : null);
  }

  async function guardarCalificacion({ valor, texto }: { valor: number; texto: string }) {
    if (!calificando) return;
    const { item, enGrilla, propia } = calificando;
    if (propia) {
      // Ya tenía nota: se edita y el estado no cambia (como en la ficha).
      const { aviso } = await editarCalificacion(propia, valor, texto);
      if (aviso) toast.success(t(`title.feedback.${aviso}`));
      setCalificando(null);
      return;
    }
    await crearCalificacion({ idTmdb: item.id_tmdb, tipo: item.tipo, valor, texto });
    setCalificando(null);
    if (enGrilla) viendo.avisarCalificadaYMovida(item, valor);
    else viendo.avisarCalificada({ valor, conResena: Boolean(texto) });
  }

  // «Open Watchlist» va a la lista Pendientes, que se busca por su clave.
  const esViendo = lista?.clave === "viendo";
  const vaciaViendo = esViendo && lista?.cantidad_items === 0;
  useEffect(() => {
    if (!vaciaViendo || idPendientes !== null) return;
    let vigente = true;
    apiFetch<ResumenLista[]>("/api/lists/").then(
      (todas) =>
        vigente && setIdPendientes(todas.find((otra) => otra.clave === "pendientes")?.id ?? null),
      () => undefined
    );
    return () => {
      vigente = false;
    };
  }, [vaciaViendo, idPendientes]);

  async function quitar(item: ItemLista) {
    await apiFetch(`/api/lists/${id}/items/${item.item_id}/`, { method: "DELETE" });
    sacarDeLaGrilla(item);
    setAccion(null);
    toast.success(t("lists.feedback.itemRemoved"));
  }

  async function renombrar(nombre: string) {
    const actualizada = await apiFetch<ResumenLista>(`/api/lists/${id}/`, {
      method: "PUT",
      body: { nombre },
    });
    setLista((actual) => (actual ? { ...actual, ...actualizada } : actual));
    setDialogo(null);
    toast.success(t("lists.feedback.renamed"));
  }

  async function eliminar() {
    await apiFetch(`/api/lists/${id}/`, { method: "DELETE" });
    toast.success(t("lists.feedback.deleted"));
    router.push(routes.lists);
  }

  if (noExiste) notFound();

  const nombre = lista ? nombreDe(lista) : null;
  const select =
    "h-9 min-w-0 cursor-pointer rounded-full border-0 bg-raised-2 px-2.5 text-center text-sm font-semibold text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";
  const caja = (activo: boolean) =>
    cn(
      "flex h-11 min-w-0 flex-none items-center gap-2 rounded-full py-0 pr-1 pl-3.5 text-sm whitespace-nowrap text-fg-3",
      activo ? "shadow-[inset_0_0_0_1px_var(--fg-3)]" : "shadow-[inset_0_0_0_1px_var(--line)]"
    );
  // Una lápida llega sin título: en los avisos y diálogos se nombra con su leyenda.
  const tituloDe = (item: ItemLista) =>
    item.disponible ? item.titulo : t("common.content.titleUnavailable");
  const etiquetaNota = (nota: (typeof NOTAS)[number]) => t(`common.filters.${ETIQUETA_NOTA[nota]}`);
  const chips = [
    filtros.clase && {
      etiqueta: t(`common.content.${ETIQUETA_CLASE[filtros.clase]}`),
      quitar: () => cambiar({ clase: null }),
    },
    filtros.nota && {
      etiqueta: `${t("common.rating.tmdbLabel")} ${etiquetaNota(filtros.nota)}`,
      quitar: () => cambiar({ nota: null }),
    },
  ].filter((chip) => chip !== null);

  const vacia = lista !== null && lista.cantidad_items === 0;
  const sinCoincidencias = datos !== null && !vacia && datos.items.length === 0;
  // Una lista sin ítems dice solo «0 ítems»: el desglose «· 0 películas · 0 series» sobra.
  const resumen = lista
    ? (vacia
        ? [t("lists.count.items", { count: 0 })]
        : [
            t("lists.count.items", { count: lista.cantidad_items }),
            t("lists.count.movies", { count: lista.cantidad_peliculas }),
            t("lists.count.tvShows", { count: lista.cantidad_series }),
          ]
      ).join(" · ")
    : null;

  return (
    <main
      id="contenido"
      className="page-container flex flex-col gap-5 pt-4 pb-[7.5rem] md:gap-10 md:pt-12 md:pb-24"
    >
      <div className="flex flex-col gap-2.5 md:gap-3.5">
        <Link
          href={routes.lists}
          className="-ml-2.5 inline-flex h-11 items-center gap-1 self-start px-2.5 text-[0.9375rem] font-medium text-fg-2 no-underline md:hidden"
        >
          <ChevronLeft aria-hidden="true" className="size-5" />
          {t("nav.main.lists")}
        </Link>
        <nav
          aria-label={t("nav.main.breadcrumbLabel")}
          className="hidden text-sm text-fg-2 md:block"
        >
          <ol className="flex flex-wrap items-center gap-2">
            <li>
              <Link href={routes.lists} className="text-fg-2 hover:text-foreground">
                {t("nav.main.lists")}
              </Link>
            </li>
            <li aria-hidden="true">›</li>
            <li aria-current="page" className="font-semibold text-foreground">
              {nombre ?? ""}
            </li>
          </ol>
        </nav>
        <div className="flex items-start justify-between gap-3">
          {/* El conteo va en la línea del título (canvas «Watching · list page»);
              en celular solo dice cuántos ítems, en escritorio el desglose. */}
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1 md:gap-x-5">
            <h1
              ref={titulo}
              tabIndex={-1}
              className="font-display text-[3rem] leading-none break-words focus-visible:outline-2 focus-visible:outline-ring md:text-[4.5rem] md:leading-[0.95]"
            >
              {nombre ?? <span className="sr-only">{t("lists.detail.loading")}</span>}
            </h1>
            {lista && (
              <p className="text-sm text-fg-2 md:text-base">
                <span className="md:hidden">
                  {t("lists.count.items", { count: lista.cantidad_items })}
                </span>
                <span className="hidden md:inline">{resumen}</span>
              </p>
            )}
          </div>
          {lista && !esPredeterminada(lista) && nombre && (
            <ListActionsMenu
              className="mt-1 flex-none md:mt-3"
              etiqueta={t("lists.detail.actionsLabel", { listName: nombre })}
              titulo={nombre}
              acciones={[
                {
                  id: "rename",
                  etiqueta: t("common.lists.rename"),
                  onSelect: () => setDialogo("renombrar"),
                },
                {
                  id: "delete",
                  etiqueta: t("common.lists.delete"),
                  destructiva: true,
                  onSelect: () => setDialogo("eliminar"),
                },
              ]}
            />
          )}
        </div>
      </div>

      {errorCuenta ? (
        <ErrorRetry mensaje={errorCuenta} onReintentar={() => void recargar()} boton="pildora" />
      ) : errorLista ? (
        <ErrorRetry
          mensaje={t("lists.detail.loadError")}
          onReintentar={reintentar}
          boton="pildora"
        />
      ) : (
        <>
          {lista && !vacia && (
            <div className="flex flex-col gap-3 md:gap-3.5">
              <div
                role="search"
                aria-label={t("lists.detail.filterLabel", { listName: nombre ?? "" })}
                className="flex gap-2.5 md:gap-3"
              >
                <div className="relative min-w-0 flex-1">
                  <label htmlFor={`${ids}-q`} className="sr-only">
                    {t("lists.detail.searchLabel", { listName: nombre ?? "" })}
                  </label>
                  <Search
                    aria-hidden="true"
                    className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-fg-3"
                  />
                  <input
                    ref={campo}
                    id={`${ids}-q`}
                    type="search"
                    value={texto}
                    maxLength={MAX_TEXTO}
                    onChange={(evento) => setTexto(evento.target.value)}
                    placeholder={t("lists.detail.searchPlaceholder")}
                    className="h-12 w-full rounded-full border-0 bg-raised px-11 text-base font-medium md:text-[0.9375rem] text-foreground shadow-[inset_0_0_0_1px_var(--field-border)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring [&::-webkit-search-cancel-button]:hidden"
                  />
                  {texto && (
                    <button
                      type="button"
                      aria-label={t("search.input.clearLabel")}
                      onClick={() => {
                        setTexto("");
                        cambiar({ q: "" });
                        campo.current?.focus();
                      }}
                      className="absolute top-1/2 right-0.5 grid size-11 -translate-y-1/2 cursor-pointer place-items-center rounded-full text-fg-3 focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <X aria-hidden="true" className="size-4" />
                    </button>
                  )}
                </div>
                <button
                  type="button"
                  aria-haspopup="dialog"
                  aria-label={t("reviews.filters.openLabel", { activeCount: activos })}
                  onClick={() => setHoja(true)}
                  className="flex h-12 flex-none cursor-pointer items-center gap-2 rounded-full bg-raised px-4 text-sm font-semibold shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-ring md:hidden"
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

              {/* Escritorio: tipo, nota de TMDB y orden en una fila. */}
              <div className="hidden flex-wrap items-center gap-2.5 md:flex">
                <label className={caja(filtros.clase !== null)}>
                  {t("common.content.typeShortLabel")}
                  <select
                    value={filtros.clase ?? ""}
                    onChange={(evento) =>
                      cambiar({
                        clase: CLASES.find((valor) => valor === evento.target.value) ?? null,
                      })
                    }
                    className={select}
                  >
                    <option value="">{t("common.content.all")}</option>
                    {CLASES.map((valor) => (
                      <option key={valor} value={valor}>
                        {t(`common.content.${ETIQUETA_CLASE[valor]}`)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={caja(filtros.nota !== null)}>
                  {t("common.rating.tmdbLabel")}
                  <select
                    value={filtros.nota ?? ""}
                    onChange={(evento) =>
                      cambiar({
                        nota: NOTAS.find((valor) => valor === evento.target.value) ?? null,
                      })
                    }
                    className={select}
                  >
                    <option value="">{t("common.filters.anyRating")}</option>
                    {NOTAS.map((valor) => (
                      <option key={valor} value={valor}>
                        {etiquetaNota(valor)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={caja(false)}>
                  {t("common.filters.sortLabel")}
                  <select
                    value={filtros.orden}
                    onChange={(evento) =>
                      cambiar({
                        orden:
                          ORDENES_LISTA.find((valor) => valor === evento.target.value) ?? "recent",
                      })
                    }
                    className={select}
                  >
                    {ORDENES_LISTA.map((valor) => (
                      <option key={valor} value={valor}>
                        {t(ETIQUETA_ORDEN_LISTA[valor])}
                      </option>
                    ))}
                  </select>
                </label>
                {filtrando && (
                  <button
                    type="button"
                    onClick={limpiar}
                    className="h-11 flex-none cursor-pointer px-1.5 text-sm font-semibold text-fg-2 underline underline-offset-[3px] focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    {t("common.filters.clear")}
                  </button>
                )}
              </div>

              {/* Celular: el orden elegido y un chip por filtro, que lo quita. */}
              <div className="flex flex-wrap items-center gap-2 md:hidden">
                <span className="inline-flex h-8 items-center text-[0.8125rem] text-fg-3">
                  {t("lists.detail.sortPrefix", {
                    sortLabel: t(ETIQUETA_ORDEN_LISTA[filtros.orden]),
                  })}
                </span>
                {chips.map((chip) => (
                  <button
                    key={chip.etiqueta}
                    type="button"
                    onClick={chip.quitar}
                    aria-label={t("lists.detail.removeChipLabel", { filterLabel: chip.etiqueta })}
                    className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-full bg-raised-2 pr-2 pl-3 text-[0.8125rem] font-semibold focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    {chip.etiqueta}
                    <X aria-hidden="true" className="size-[0.8125rem]" />
                  </button>
                ))}
              </div>

              {/* El contenedor vive siempre; el aviso se agrega después y se anuncia. */}
              <div role="status" className="empty:sr-only">
                {filtrando && datos && lista && (
                  <p className="text-sm text-fg-3">
                    {t("lists.detail.displayedCount", {
                      shownCount: formats.number(datos.total),
                      totalCount: lista.cantidad_items,
                    })}
                  </p>
                )}
              </div>
            </div>
          )}

          {(datos === null || lista === null) && estado !== "error" && (
            <ul
              role="status"
              aria-label={t("lists.detail.loading")}
              className="grid grid-cols-2 gap-x-3.5 gap-y-6 md:grid-cols-[repeat(var(--cols),minmax(0,1fr))] md:gap-x-6 md:gap-y-9"
            >
              {[0, 1, 2, 3].map((indice) => (
                <li key={indice} className="flex flex-col gap-2.5">
                  <span className="block aspect-[2/3] w-full rounded-lg bg-raised" />
                  <span className="h-4 w-3/4 rounded bg-raised" />
                </li>
              ))}
            </ul>
          )}

          {estado === "error" && (
            <ErrorRetry
              mensaje={t("lists.detail.loadError")}
              onReintentar={reintentar}
              boton="pildora"
              className="border-t border-line py-10"
            />
          )}

          {vacia && estado === "listo" && (
            <div className="flex flex-col items-start gap-3 border-t border-line py-10">
              <h2 className="font-display text-[1.875rem] leading-none md:text-[2.125rem]">
                {t(esViendo ? "lists.watching.emptyTitle" : "lists.detail.emptyTitle")}
              </h2>
              <p className="max-w-[52ch] text-fg-2">
                {t(esViendo ? "lists.watching.emptyDescription" : "lists.detail.emptyDescription")}
              </p>
              {esViendo ? (
                <Link
                  href={idPendientes !== null ? routes.list(idPendientes) : routes.lists}
                  className="inline-flex h-12 items-center gap-2 rounded-full bg-raised-2 px-5 font-semibold text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring md:h-11 md:px-[1.125rem]"
                >
                  <Clock aria-hidden="true" className="size-[1.125rem]" />
                  {t("lists.watching.openWatchlist")}
                </Link>
              ) : (
                <Link
                  href={routes.search}
                  className="inline-flex h-11 items-center rounded-full bg-raised-2 px-[1.125rem] font-semibold text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring"
                >
                  {t("common.actions.explore")}
                </Link>
              )}
            </div>
          )}

          <div role="status" className="empty:sr-only">
            {sinCoincidencias && estado === "listo" && (
              <div className="flex flex-col items-start gap-3 border-t border-line py-10">
                <p className="text-fg-2">{t("lists.detail.filteredEmpty")}</p>
                <button
                  type="button"
                  onClick={limpiar}
                  className="h-11 cursor-pointer rounded-full bg-raised-2 px-[1.125rem] font-semibold focus-visible:outline-2 focus-visible:outline-ring"
                >
                  {t("common.filters.clear")}
                </button>
              </div>
            )}
          </div>

          {datos && datos.items.length > 0 && estado !== "error" && nombre && (
            <div aria-busy={estado === "cargando"} className="flex flex-col">
              <ul className="grid grid-cols-2 gap-x-3.5 gap-y-6 md:grid-cols-[repeat(var(--cols),minmax(0,1fr))] md:gap-x-6 md:gap-y-9">
                {datos.items.map((item) => (
                  <li key={item.item_id} className="group/item relative list-none">
                    {item.disponible ? (
                      <MediaCard
                        title={itemATitulo(item)}
                        showType
                        showUnrated
                        fluid
                        addedAt={item.fecha_agregado}
                        addedKind={esViendo ? "started" : "added"}
                        from={`list-${id}`}
                      />
                    ) : (
                      <UnavailableCard
                        addedAt={item.fecha_agregado}
                        addedKind={esViendo ? "started" : "added"}
                      />
                    )}
                    {esViendo ? (
                      item.disponible && (
                        <WatchingCardMenu
                          titulo={item.titulo}
                          abierto={menuAbierto === item.item_id}
                          onAbrir={() => setMenuAbierto(item.item_id)}
                          onCerrar={() => setMenuAbierto(null)}
                          onElegir={(accion) => elegirDelMenu(item, accion)}
                        />
                      )
                    ) : (
                      <button
                        type="button"
                        aria-label={t("lists.detail.removeItemLabel", {
                          title: tituloDe(item),
                          listName: nombre,
                        })}
                        onClick={() => setAccion({ tipo: "quitar", item })}
                        className="absolute top-2 right-2 grid size-11 cursor-pointer place-items-center rounded-full bg-black/70 text-white opacity-0 backdrop-blur-sm transition-opacity group-focus-within/item:opacity-100 group-hover/item:opacity-100 focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-ring motion-reduce:transition-none [@media(hover:none)]:opacity-100"
                      >
                        <X aria-hidden="true" className="size-5" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
              {mas === "error" && (
                <ErrorRetry
                  mensaje={t("lists.detail.loadError")}
                  onReintentar={cargarMas}
                  boton="pildora"
                  className="pt-6"
                />
              )}
              {datos.next && mas !== "error" && (
                <div ref={centinela} className="flex justify-center pt-6">
                  <button
                    type="button"
                    onClick={cargarMas}
                    disabled={mas === "cargando"}
                    className="inline-flex h-11 cursor-pointer items-center gap-2 rounded-full bg-raised-2 px-[1.125rem] font-semibold focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-wait"
                  >
                    {mas === "cargando" && (
                      <LoaderCircle
                        aria-hidden="true"
                        className="size-4 motion-safe:animate-spin"
                      />
                    )}
                    {t("lists.detail.loadMore")}
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {hoja && (
        <ListFiltersSheet
          filtros={filtros}
          total={estado === "listo" ? (datos?.total ?? null) : null}
          onCambiar={cambiar}
          onLimpiar={limpiar}
          onClose={() => setHoja(false)}
        />
      )}
      {dialogo === "renombrar" && lista && (
        <ListNameDialog
          modo="renombrar"
          inicial={lista.nombre}
          onSubmit={renombrar}
          onClose={() => setDialogo(null)}
        />
      )}
      {dialogo === "eliminar" && lista && (
        <ConfirmDialog
          titulo={t("lists.delete.confirmTitle", { listName: lista.nombre })}
          descripcion={t("lists.delete.confirmDescription")}
          confirmar={t("common.actions.delete")}
          onConfirm={eliminar}
          onCancel={() => setDialogo(null)}
        />
      )}
      {accion?.tipo === "quitar" && nombre && (
        <ConfirmDialog
          titulo={t("lists.detail.removeConfirmTitle", {
            title: tituloDe(accion.item),
            listName: nombre,
          })}
          confirmar={t("common.actions.remove")}
          onConfirm={() => quitar(accion.item)}
          onCancel={() => setAccion(null)}
        />
      )}
      {calificando && (
        <RatingDialog
          titulo={tituloDe(calificando.item)}
          enVistas={!calificando.enGrilla}
          enViendo={calificando.enGrilla}
          inicial={
            calificando.propia
              ? {
                  valor: calificando.propia.valor,
                  texto: calificando.propia.texto,
                  moderada: calificando.propia.moderada,
                }
              : undefined
          }
          onSubmit={guardarCalificacion}
          onClose={() => setCalificando(null)}
        />
      )}
    </main>
  );
}
