"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { notFound, useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, LoaderCircle, Search, SlidersHorizontal, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount } from "@/components/AccountProvider";
import { ListActionsMenu } from "@/components/features/lists/ListActionsMenu";
import { useNombreLista } from "@/components/features/lists/ListCard";
import { ListFiltersSheet } from "@/components/features/lists/ListFiltersSheet";
import { ListNameDialog } from "@/components/features/lists/ListNameDialog";
import { MediaCard } from "@/components/features/MediaCard";
import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
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
import { routes } from "@/lib/routes";
import { ETIQUETA_NOTA, NOTAS } from "@/lib/search";
import type { MiCalificacion } from "@/lib/title";
import { cn } from "@/lib/utils";

/** Espera después de la última tecla antes de filtrar, como Buscar. */
const ESPERA_MS = 350;
/** Distancia al final de la grilla a la que se pide la página siguiente. */
const ANTICIPO = "600px";

type Datos = { items: ItemLista[]; next: string | null; total: number };
type Accion =
  { tipo: "quitar"; item: ItemLista } | { tipo: "vistas"; item: ItemLista; texto: string | null };

/**
 * Detalle de una lista según el canvas «List detail» (L-03). Los filtros viven
 * en la URL; los ítems se piden por cursor a `GET /api/lists/{id}/items/`.
 * Quitar de «Watched» un título calificado responde 409 (Conflict): se pide
 * confirmar el borrado de la calificación y se reintenta con
 * `?borrar_calificacion=true`, igual que en la ficha.
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
  const [datos, setDatos] = useState<Datos | null>(null);
  const [estado, setEstado] = useState<"cargando" | "listo" | "error">("cargando");
  const [mas, setMas] = useState<"quieto" | "cargando" | "error">("quieto");
  const [intento, setIntento] = useState(0);
  const [hoja, setHoja] = useState(false);
  const [dialogo, setDialogo] = useState<"renombrar" | "eliminar" | null>(null);
  const [accion, setAccion] = useState<Accion | null>(null);
  const pedido = useRef(0);
  const centinela = useRef<HTMLDivElement>(null);
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

  // Primera página de cada combinación de filtros. Mientras llega la nueva
  // queda la anterior a la vista; una respuesta vieja se descarta.
  useEffect(() => {
    if (!perfil?.pk) return;
    const pedidoId = ++pedido.current;
    setEstado("cargando");
    apiFetch<PaginaItems>(consulta).then(
      (pagina) => {
        if (pedidoId !== pedido.current) return;
        setDatos({ items: pagina.results, next: pagina.next, total: pagina.total });
        setEstado("listo");
        setMas("quieto");
      },
      () => {
        if (pedidoId === pedido.current) setEstado("error");
      }
    );
  }, [consulta, perfil?.pk, intento]);

  function cargarMas() {
    if (!datos?.next || mas === "cargando" || estado !== "listo") return;
    const pedidoId = pedido.current;
    setMas("cargando");
    apiFetch<PaginaItems>(rutaPaginaItems(id, datos.next)).then(
      (pagina) => {
        if (pedidoId !== pedido.current) return;
        setDatos((actual) =>
          actual
            ? { ...actual, items: combinarItems(actual.items, pagina.results), next: pagina.next }
            : actual
        );
        setMas("quieto");
      },
      () => {
        if (pedidoId === pedido.current) setMas("error");
      }
    );
  }

  // Carga al bajar; el botón «Cargar más» queda para teclado y como respaldo.
  useEffect(() => {
    if (!datos?.next || mas !== "quieto" || estado !== "listo" || !centinela.current) return;
    const observador = new IntersectionObserver(
      ([entrada]) => {
        if (entrada.isIntersecting) cargarMas();
      },
      { rootMargin: ANTICIPO }
    );
    observador.observe(centinela.current);
    return () => observador.disconnect();
  });

  function sacarDeLaGrilla(item: ItemLista) {
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
  }

  async function quitar(item: ItemLista) {
    try {
      await apiFetch(`/api/lists/${id}/items/${item.item_id}/`, { method: "DELETE" });
    } catch (motivo) {
      if (!(motivo instanceof ApiError) || motivo.code !== "rating_blocks_removal_from_watched")
        throw motivo;
      // Calificado en «Watched»: se pide confirmar el borrado de la calificación.
      // El texto de la reseña, si hay, se muestra en la confirmación.
      const propia = await apiFetch<MiCalificacion | null>(
        `/api/reviews/mias/?id_tmdb=${item.id_tmdb}&tipo=${item.tipo}`
      ).catch(() => null);
      setAccion({ tipo: "vistas", item, texto: propia?.texto ?? null });
      return;
    }
    sacarDeLaGrilla(item);
    setAccion(null);
    toast.success(t("lists.feedback.itemRemoved"));
  }

  async function quitarConCalificacion(item: ItemLista, conTexto: boolean) {
    await apiFetch(`/api/lists/${id}/items/${item.item_id}/?borrar_calificacion=true`, {
      method: "DELETE",
    });
    sacarDeLaGrilla(item);
    setAccion(null);
    toast.success(
      t(conTexto ? "title.feedback.ratingReviewDeleted" : "title.feedback.ratingDeleted")
    );
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
  const resumen = lista
    ? [
        t("lists.count.items", { count: lista.cantidad_items }),
        t("lists.count.movies", { count: lista.cantidad_peliculas }),
        t("lists.count.tvShows", { count: lista.cantidad_series }),
      ].join(" · ")
    : null;

  return (
    <main
      id="contenido"
      className="mx-auto flex max-w-[1360px] flex-col gap-5 px-5 pt-4 pb-[120px] md:gap-10 md:px-10 md:pt-12 md:pb-24"
    >
      <div className="flex flex-col gap-2.5 md:gap-3.5">
        <Link
          href={routes.lists}
          className="-ml-2.5 inline-flex h-11 items-center gap-1 self-start px-2.5 text-[15px] font-medium text-fg-2 no-underline md:hidden"
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
          <div className="flex min-w-0 flex-col gap-2 md:gap-3">
            <h1
              ref={titulo}
              tabIndex={-1}
              className="font-display text-[48px] leading-none break-words focus-visible:outline-2 focus-visible:outline-ring md:text-[72px] md:leading-[0.95]"
            >
              {nombre ?? <span className="sr-only">{t("lists.detail.loading")}</span>}
            </h1>
            {resumen && <p className="text-fg-2">{resumen}</p>}
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
          onReintentar={() => setIntento((anterior) => anterior + 1)}
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
                    className="h-12 w-full rounded-full border-0 bg-raised px-11 text-base font-medium md:text-[15px] text-foreground shadow-[inset_0_0_0_1px_var(--line)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring [&::-webkit-search-cancel-button]:hidden"
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
                <span className="inline-flex h-8 items-center text-[13px] text-fg-3">
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
                    className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-full bg-raised-2 pr-2 pl-3 text-[13px] font-semibold focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    {chip.etiqueta}
                    <X aria-hidden="true" className="size-[13px]" />
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
              className="grid grid-cols-2 gap-x-3.5 gap-y-6 md:grid-cols-[repeat(auto-fill,minmax(min(220px,100%),1fr))] md:gap-x-6 md:gap-y-9"
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
              onReintentar={() => setIntento((anterior) => anterior + 1)}
              boton="pildora"
              className="border-t border-line py-10"
            />
          )}

          {vacia && estado === "listo" && (
            <div className="flex flex-col items-start gap-3 border-t border-line py-10">
              <h2 className="font-display text-[30px] leading-none md:text-[34px]">
                {t("lists.detail.emptyTitle")}
              </h2>
              <p className="max-w-[52ch] text-fg-2">{t("lists.detail.emptyDescription")}</p>
              <Link
                href={routes.search}
                className="inline-flex h-11 items-center rounded-full bg-raised-2 px-[18px] font-semibold text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring"
              >
                {t("common.actions.explore")}
              </Link>
            </div>
          )}

          <div role="status" className="empty:sr-only">
            {sinCoincidencias && estado === "listo" && (
              <div className="flex flex-col items-start gap-3 border-t border-line py-10">
                <p className="text-fg-2">{t("lists.detail.filteredEmpty")}</p>
                <button
                  type="button"
                  onClick={limpiar}
                  className="h-11 cursor-pointer rounded-full bg-raised-2 px-[18px] font-semibold focus-visible:outline-2 focus-visible:outline-ring"
                >
                  {t("common.filters.clear")}
                </button>
              </div>
            )}
          </div>

          {datos && datos.items.length > 0 && estado !== "error" && nombre && (
            <div aria-busy={estado === "cargando"} className="flex flex-col">
              <ul className="grid grid-cols-2 gap-x-3.5 gap-y-6 md:grid-cols-[repeat(auto-fill,minmax(min(220px,100%),1fr))] md:gap-x-6 md:gap-y-9">
                {datos.items.map((item) => (
                  <li key={item.item_id} className="group/item relative list-none">
                    <MediaCard
                      title={itemATitulo(item)}
                      showType
                      showUnrated
                      fluid
                      addedAt={item.fecha_agregado}
                      from={`list-${id}`}
                    />
                    <button
                      type="button"
                      aria-label={t("lists.detail.removeItemLabel", {
                        title: item.titulo,
                        listName: nombre,
                      })}
                      onClick={() => setAccion({ tipo: "quitar", item })}
                      className="absolute top-2 right-2 grid size-11 cursor-pointer place-items-center rounded-full bg-black/70 text-white opacity-0 backdrop-blur-sm transition-opacity group-focus-within/item:opacity-100 group-hover/item:opacity-100 focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-ring motion-reduce:transition-none [@media(hover:none)]:opacity-100"
                    >
                      <X aria-hidden="true" className="size-5" />
                    </button>
                  </li>
                ))}
              </ul>
              {mas === "error" && (
                <ErrorRetry
                  mensaje={t("lists.detail.loadError")}
                  onReintentar={() => {
                    setMas("quieto");
                    cargarMas();
                  }}
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
                    className="inline-flex h-11 cursor-pointer items-center gap-2 rounded-full bg-raised-2 px-[18px] font-semibold focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-wait"
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
            title: accion.item.titulo,
            listName: nombre,
          })}
          confirmar={t("common.actions.remove")}
          onConfirm={() => quitar(accion.item)}
          onCancel={() => setAccion(null)}
        />
      )}
      {accion?.tipo === "vistas" && (
        <ConfirmDialog
          titulo={t("title.watched.removeConfirmTitle")}
          descripcion={t(
            accion.texto
              ? "title.rating.removeBothDescription"
              : "title.rating.removeOnlyDescription",
            { title: accion.item.titulo }
          )}
          preview={accion.texto}
          confirmar={t("title.watched.remove")}
          onConfirm={() => quitarConCalificacion(accion.item, Boolean(accion.texto))}
          onCancel={() => setAccion(null)}
        />
      )}
    </main>
  );
}
