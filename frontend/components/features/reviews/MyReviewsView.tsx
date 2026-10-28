"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ChevronLeft, LoaderCircle, Search, SlidersHorizontal, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount } from "@/components/AccountProvider";
import { ErrorRetry } from "@/components/ui/ErrorRetry";
import { MyReviewItem, type AccionResena } from "@/components/features/reviews/MyReviewItem";
import {
  ETIQUETA_CLASE,
  ETIQUETA_PRESENCIA,
  ReviewFiltersSheet,
} from "@/components/features/reviews/ReviewFiltersSheet";
import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { RatingDialog } from "@/components/features/title/RatingDialog";
import { apiFetch } from "@/lib/api";
import {
  CLASES,
  FILTROS_VACIOS,
  MAX_TEXTO,
  PRESENCIAS,
  consultaApi,
  filtrosActivos,
  filtrosDesdeUrl,
  guardarUltimasResenas,
  hayFiltros,
  urlDeFiltros,
  type FiltrosResenas,
} from "@/lib/my-reviews";
import { ETIQUETA_ORDEN, ORDENES } from "@/lib/review-filters";
import { combinarResenas, rutaPagina, type MiResena, type PaginaResenas } from "@/lib/reviews";
import { routes } from "@/lib/routes";
import { ETIQUETA_NOTA, NOTAS } from "@/lib/search";
import { planEdicion } from "@/lib/title";
import { cn } from "@/lib/utils";

/** Espera después de la última tecla antes de filtrar, como Buscar. */
const ESPERA_MS = 350;
/** Distancia al final de la lista a la que se pide la página siguiente. */
const ANTICIPO = "600px";

type Datos = {
  items: MiResena[];
  next: string | null;
  total: number;
  /** Calificaciones de la cuenta sin filtros: distingue «nada calificado» de «nada con estos filtros». */
  totalPropias: number;
};

/**
 * «Calificaciones y reseñas» según el canvas. Los filtros viven en la URL y se
 * cambian con la History API, como Buscar. La lista se pide a
 * `GET /api/reviews/mias/` (filtrada en el backend, por cursor) y se edita con
 * los mismos diálogos de la ficha.
 */
export function MyReviewsView() {
  const t = useTranslations();
  const { perfil, error: errorCuenta, recargar } = useAccount();
  const filtros = filtrosDesdeUrl(useSearchParams());
  const consulta = consultaApi(filtros);
  const [texto, setTexto] = useState(filtros.q);
  const [datos, setDatos] = useState<Datos | null>(null);
  const [estado, setEstado] = useState<"cargando" | "listo" | "error">("cargando");
  const [mas, setMas] = useState<"quieto" | "cargando" | "error">("quieto");
  const [intento, setIntento] = useState(0);
  const [hoja, setHoja] = useState(false);
  const [accion, setAccion] = useState<{ item: MiResena; tipo: AccionResena } | null>(null);
  const pedido = useRef(0);
  const centinela = useRef<HTMLDivElement>(null);
  const titulo = useRef<HTMLHeadingElement>(null);
  const campo = useRef<HTMLInputElement>(null);
  const ids = useId();
  const activos = filtrosActivos(filtros);
  const filtrando = hayFiltros(filtros);

  // Parte de la URL de ahora y no de lo renderizado: la espera del texto y
  // «limpiar» pueden cruzarse antes de que `useSearchParams` se entere, y la
  // espera devolvía los filtros ya quitados.
  function cambiar(cambios: Partial<FiltrosResenas>) {
    const actuales = filtrosDesdeUrl(new URLSearchParams(window.location.search));
    window.history.replaceState(null, "", urlDeFiltros({ ...actuales, ...cambios }));
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

  // La miga «Calificaciones y reseñas» de la ficha vuelve a esta lista filtrada.
  const url = urlDeFiltros(filtros);
  useEffect(() => guardarUltimasResenas(url), [url]);

  // Primera página de cada combinación de filtros. Mientras llega la nueva
  // queda la anterior a la vista; una respuesta vieja se descarta.
  useEffect(() => {
    if (!perfil?.pk) return;
    const id = ++pedido.current;
    setEstado("cargando");
    apiFetch<PaginaResenas>(consulta).then(
      (pagina) => {
        if (id !== pedido.current) return;
        setDatos({
          items: pagina.results,
          next: pagina.next,
          total: pagina.total,
          totalPropias: pagina.total_propias ?? pagina.total,
        });
        setEstado("listo");
        setMas("quieto");
      },
      () => {
        if (id === pedido.current) setEstado("error");
      }
    );
  }, [consulta, perfil?.pk, intento]);

  function cargarMas() {
    if (!datos?.next || mas === "cargando" || estado !== "listo") return;
    const id = pedido.current;
    setMas("cargando");
    apiFetch<PaginaResenas>(rutaPagina(datos.next)).then(
      (pagina) => {
        if (id !== pedido.current) return;
        setDatos((actual) =>
          actual
            ? {
                ...actual,
                items: combinarResenas(actual.items, pagina.results),
                next: pagina.next,
              }
            : actual
        );
        setMas("quieto");
      },
      () => {
        if (id === pedido.current) setMas("error");
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

  function reemplazar(actualizado: MiResena) {
    setDatos((actual) =>
      actual
        ? {
            ...actual,
            items: actual.items.map((item) => (item.id === actualizado.id ? actualizado : item)),
          }
        : actual
    );
  }

  // Lo editado queda en su lugar aunque deje de coincidir con los filtros: que
  // la fila desaparezca bajo el foco desorienta. La próxima carga lo acomoda.
  async function guardar(item: MiResena, { valor, texto }: { valor: number; texto: string }) {
    const plan = planEdicion(item, valor, texto);
    let actual = item;
    if (plan.borrarTexto) {
      await apiFetch(`/api/reviews/${item.id}/texto/`, { method: "DELETE" });
      actual = { ...actual, texto: null };
    }
    if (Object.keys(plan.cambios).length) {
      const respuesta = await apiFetch<Partial<MiResena>>(`/api/reviews/${item.id}/`, {
        method: "PUT",
        body: plan.cambios,
      });
      actual = { ...actual, ...plan.cambios, ...respuesta, id: item.id };
    }
    reemplazar(actual);
    setAccion(null);
    const nota = "valor" in plan.cambios;
    const textoCambio = "texto" in plan.cambios || plan.borrarTexto;
    if (nota && textoCambio) toast.success(t("title.feedback.ratingReviewUpdated"));
    else if (nota) toast.success(t("title.feedback.ratingUpdated"));
    else if (plan.borrarTexto) toast.success(t("title.feedback.reviewDeleted"));
    else if (textoCambio) toast.success(t("title.feedback.reviewUpdated"));
  }

  async function borrarTexto(item: MiResena) {
    await apiFetch(`/api/reviews/${item.id}/texto/`, { method: "DELETE" });
    reemplazar({ ...item, texto: null });
    setAccion(null);
    toast.success(t("title.feedback.reviewDeleted"));
  }

  async function quitar(item: MiResena) {
    await apiFetch(`/api/reviews/${item.id}/`, { method: "DELETE" });
    setDatos((actual) =>
      actual
        ? {
            ...actual,
            items: actual.items.filter((otro) => otro.id !== item.id),
            total: actual.total - 1,
            totalPropias: actual.totalPropias - 1,
          }
        : actual
    );
    setAccion(null);
    toast.success(
      t(item.texto ? "title.feedback.ratingReviewDeleted" : "title.feedback.ratingDeleted")
    );
    // La fila ya no existe: el foco va al título de la página.
    requestAnimationFrame(() => titulo.current?.focus());
  }

  const select =
    "h-9 min-w-0 flex-1 cursor-pointer rounded-full border-0 bg-raised-2 px-2.5 text-center text-sm font-semibold text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";
  const caja = (activo: boolean) =>
    cn(
      "flex h-11 min-w-0 flex-auto items-center gap-2 rounded-full py-0 pr-1 pl-3.5 text-sm whitespace-nowrap text-fg-3",
      activo ? "shadow-[inset_0_0_0_1px_var(--fg-3)]" : "shadow-[inset_0_0_0_1px_var(--line)]"
    );
  const etiquetaNota = (nota: (typeof NOTAS)[number]) => t(`common.filters.${ETIQUETA_NOTA[nota]}`);
  const chips = [
    filtros.resena && {
      etiqueta: t(`reviews.filters.${ETIQUETA_PRESENCIA[filtros.resena]}`),
      quitar: () => cambiar({ resena: null }),
    },
    filtros.clase && {
      etiqueta: t(`common.content.${ETIQUETA_CLASE[filtros.clase]}`),
      quitar: () => cambiar({ clase: null }),
    },
    filtros.nota && {
      etiqueta: t("reviews.filters.ratingChip", { rating: etiquetaNota(filtros.nota) }),
      quitar: () => cambiar({ nota: null }),
    },
  ].filter((chip) => chip !== null);

  const sinNada = datos !== null && datos.totalPropias === 0;
  const sinCoincidencias = datos !== null && !sinNada && datos.items.length === 0;

  return (
    <main
      id="contenido"
      className="mx-auto flex max-w-[1080px] flex-col gap-5 px-5 pt-4 pb-[120px] md:gap-10 md:px-10 md:pt-12 md:pb-24"
    >
      <div className="flex flex-col gap-2.5 md:gap-3.5">
        <Link
          href={routes.profile}
          className="-ml-2.5 inline-flex h-11 items-center gap-1 self-start px-2.5 text-[15px] font-medium text-fg-2 no-underline md:hidden"
        >
          <ChevronLeft aria-hidden="true" className="size-5" />
          {t("nav.main.profileShort")}
        </Link>
        <nav
          aria-label={t("nav.main.breadcrumbLabel")}
          className="hidden text-sm text-fg-2 md:block"
        >
          <ol className="flex flex-wrap items-center gap-2">
            <li>
              <Link href={routes.profile} className="text-fg-2 hover:text-foreground">
                {t("nav.main.profileShort")}
              </Link>
            </li>
            <li aria-hidden="true">›</li>
            <li aria-current="page" className="font-semibold text-foreground">
              {t("nav.main.ratingsReviews")}
            </li>
          </ol>
        </nav>
        <h1
          ref={titulo}
          tabIndex={-1}
          className="mb-[15px] font-display text-[48px] leading-none focus-visible:outline-2 focus-visible:outline-ring md:text-[72px] md:leading-[0.95]"
        >
          {t("nav.main.ratingsReviews")}
        </h1>
      </div>

      {errorCuenta ? (
        <ErrorRetry mensaje={errorCuenta} onReintentar={() => void recargar()} boton="pildora" />
      ) : (
        <>
          {!sinNada && (
            <div className="flex flex-col gap-3 md:gap-3.5">
              <div
                role="search"
                aria-label={t("reviews.filters.label")}
                className="flex gap-2.5 md:gap-3"
              >
                <div className="relative min-w-0 flex-1">
                  <label htmlFor={`${ids}-q`} className="sr-only">
                    {t("reviews.filters.titleSearchLabel")}
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
                    placeholder={t("reviews.filters.titleSearchLabel")}
                    className="h-12 w-full rounded-full border-0 bg-raised px-11 text-base font-medium md:text-[15px] text-foreground shadow-[inset_0_0_0_1px_var(--field-border)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring [&::-webkit-search-cancel-button]:hidden"
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
                {filtrando && (
                  <button
                    type="button"
                    onClick={limpiar}
                    className="hidden h-12 flex-none cursor-pointer px-1.5 text-sm font-semibold text-fg-2 underline underline-offset-[3px] focus-visible:outline-2 focus-visible:outline-ring md:block"
                  >
                    {t("common.filters.clear")}
                  </button>
                )}
              </div>

              {/* Escritorio: los cuatro selectores en una fila. */}
              <div className="hidden items-center gap-2.5 md:flex">
                <label className={caja(filtros.resena !== null)}>
                  {t("reviews.filters.presenceLabel")}
                  <select
                    value={filtros.resena ?? ""}
                    onChange={(evento) =>
                      cambiar({
                        resena: PRESENCIAS.find((valor) => valor === evento.target.value) ?? null,
                      })
                    }
                    className={select}
                  >
                    <option value="">{t("reviews.filters.all")}</option>
                    {PRESENCIAS.map((valor) => (
                      <option key={valor} value={valor}>
                        {t(`reviews.filters.${ETIQUETA_PRESENCIA[valor]}`)}
                      </option>
                    ))}
                  </select>
                </label>
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
                  {t("common.rating.label")}
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
                        orden: ORDENES.find((valor) => valor === evento.target.value) ?? "newest",
                      })
                    }
                    className={select}
                  >
                    {ORDENES.map((valor) => (
                      <option key={valor} value={valor}>
                        {t(ETIQUETA_ORDEN[valor])}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {/* Celular: el orden elegido y un chip por filtro, que lo quita. */}
              <div className="flex flex-wrap items-center gap-2 md:hidden">
                <span className="inline-flex h-8 items-center text-[13px] text-fg-3">
                  {t("reviews.filters.orderPrefix", {
                    sortLabel: t(ETIQUETA_ORDEN[filtros.orden]),
                  })}
                </span>
                {chips.map((chip) => (
                  <button
                    key={chip.etiqueta}
                    type="button"
                    onClick={chip.quitar}
                    aria-label={t("reviews.filters.removeChipLabel", {
                      filterLabel: chip.etiqueta,
                    })}
                    className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-full bg-raised-2 pr-2 pl-3 text-[13px] font-semibold focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    {chip.etiqueta}
                    <X aria-hidden="true" className="size-[13px]" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {datos === null && estado !== "error" && (
            <div role="status" aria-label={t("reviews.results.loading")} className="flex flex-col">
              {[0, 1, 2].map((fila) => (
                <div
                  key={fila}
                  className="grid grid-cols-[56px_minmax(0,1fr)] gap-3.5 border-t border-line py-5 md:grid-cols-[80px_minmax(0,1fr)] md:gap-6 md:py-7"
                >
                  <div className="h-[84px] rounded-md bg-raised-2 md:h-[120px]" />
                  <div className="flex flex-col gap-3">
                    <div className="h-6 w-1/2 rounded bg-raised-2" />
                    <div className="h-4 w-1/3 rounded bg-raised-2" />
                    <div className="h-12 rounded bg-raised-2" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {estado === "error" && (
            <ErrorRetry
              mensaje={t("reviews.results.loadError")}
              onReintentar={() => setIntento((anterior) => anterior + 1)}
              boton="pildora"
              className="border-t border-line py-10"
            />
          )}

          {sinNada && estado === "listo" && (
            <div className="flex flex-col items-start gap-3 border-t border-line py-10">
              <p className="text-fg-2">{t("reviews.results.empty")}</p>
              <Link
                href={routes.search}
                className="inline-flex h-11 items-center rounded-full bg-raised-2 px-[18px] font-semibold text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring"
              >
                {t("reviews.results.emptyAction")}
              </Link>
            </div>
          )}

          {/* El contenedor vive siempre; el aviso se agrega después y se anuncia. */}
          <div role="status" className="empty:sr-only">
            {sinCoincidencias && estado !== "error" && (
              <div className="flex flex-col items-start gap-3 border-t border-line py-10">
                <p className="text-fg-2">{t("reviews.results.filteredEmpty")}</p>
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

          {datos && datos.items.length > 0 && estado !== "error" && (
            <div aria-busy={estado === "cargando"} className="flex flex-col">
              <ol className="flex flex-col">
                {datos.items.map((item) => (
                  <MyReviewItem
                    key={item.id}
                    item={item}
                    onAccion={(tipo) => setAccion({ item, tipo })}
                  />
                ))}
              </ol>
              {mas === "error" && (
                <ErrorRetry
                  mensaje={t("reviews.results.loadError")}
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
                    {t("reviews.results.loadMore")}
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {hoja && (
        <ReviewFiltersSheet
          filtros={filtros}
          total={estado === "listo" ? (datos?.total ?? null) : null}
          onCambiar={cambiar}
          onLimpiar={limpiar}
          onClose={() => setHoja(false)}
        />
      )}
      {accion?.tipo === "editar" && (
        <RatingDialog
          titulo={accion.item.titulo}
          enVistas
          inicial={{ valor: accion.item.valor, texto: accion.item.texto }}
          onSubmit={(cambios) => guardar(accion.item, cambios)}
          onRemoveRating={() => setAccion({ item: accion.item, tipo: "quitar" })}
          onClose={() => setAccion(null)}
        />
      )}
      {accion?.tipo === "borrarTexto" && (
        <ConfirmDialog
          titulo={t("title.review.deleteConfirmTitle")}
          descripcion={t("title.review.deleteConfirmDescription", { title: accion.item.titulo })}
          preview={accion.item.texto}
          confirmar={t("common.review.delete")}
          onConfirm={() => borrarTexto(accion.item)}
          onCancel={() => setAccion(null)}
        />
      )}
      {accion?.tipo === "quitar" && (
        <ConfirmDialog
          titulo={t("title.rating.removeConfirmTitle")}
          descripcion={t(
            accion.item.texto
              ? "title.rating.removeBothDescription"
              : "title.rating.removeOnlyDescription",
            { title: accion.item.titulo }
          )}
          preview={accion.item.texto}
          confirmar={t("common.rating.remove")}
          onConfirm={() => quitar(accion.item)}
          onCancel={() => setAccion(null)}
        />
      )}
    </main>
  );
}
