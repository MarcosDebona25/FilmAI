"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount } from "@/components/AccountProvider";
import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { CreditsSection } from "@/components/features/title/CreditsSection";
import { RatingDialog, mensajeDeError } from "@/components/features/title/RatingDialog";
import { TitleActions } from "@/components/features/title/TitleActions";
import { ApiError, apiFetch } from "@/lib/api";
import type { MediaType } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import { tamanioTitulo } from "@/lib/home";
import { routes } from "@/lib/routes";
import {
  normalizarFicha,
  origenDesde,
  planEdicion,
  type Creditos,
  type MiCalificacion,
  type TmdbDetalle,
} from "@/lib/title";
import type { ListaFicha } from "@/lib/title-lists";
import { useCatalog } from "@/lib/use-catalog";
import { cn } from "@/lib/utils";

const ESTRELLA =
  "12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2";
// Mismo criterio que el Home (14/10/2026): la letra se achica con el largo.
const TAMANIO_TITULO = {
  grande: "text-[48px] md:text-[120px]",
  mediano: "text-[40px] md:text-[88px]",
  chico: "text-[32px] md:text-[64px]",
} as const;
const VELO_CELULAR =
  "linear-gradient(0deg, rgb(var(--scrim)) 0%, rgb(var(--scrim) / 0.2) 60%), linear-gradient(180deg, rgb(var(--scrim) / 0.85) 0%, rgb(var(--scrim) / 0) 30%)";
const VELO_ESCRITORIO =
  "linear-gradient(0deg, rgb(var(--scrim)) 0%, rgb(var(--scrim) / 0.85) 30%, rgb(var(--scrim) / 0.2) 70%), linear-gradient(180deg, rgb(var(--scrim) / 0.8) 0%, rgb(var(--scrim) / 0) 24%)";

type Modal = null | "calificar" | "quitar";

/**
 * Ficha de una película o serie (C-07), según el canvas. Lo público (detalle y
 * créditos) se ve sin sesión; con sesión suma la calificación propia y las
 * listas, que se actualizan con lo que responde la API después de cada cambio.
 */
export function TitleView({ tipo, id }: { tipo: MediaType; id: number }) {
  const t = useTranslations();
  const formats = useFormats();
  const pathname = usePathname();
  const origen = origenDesde(useSearchParams().get("from"));
  const { perfil, cargando } = useAccount();
  const conSesion = !cargando && perfil !== null;
  const [intento, setIntento] = useState(0);
  const detalle = useCatalog<TmdbDetalle>(`/api/catalogo/${tipo}/${id}/`, intento);
  const creditos = useCatalog<Creditos>(`/api/catalogo/${tipo}/${id}/credits/`, intento);

  // `undefined` = todavía no se sabe; `null` = no calificó.
  const [mia, setMia] = useState<MiCalificacion | null | undefined>(undefined);
  const [listas, setListas] = useState<ListaFicha[] | null>(null);
  const [nombreLista, setNombreLista] = useState<string | null>(null);
  const [modal, setModal] = useState<Modal>(null);
  const [sinopsisCompleta, setSinopsisCompleta] = useState(false);

  const recargarListas = useCallback(() => {
    return apiFetch<ListaFicha[]>(`/api/lists/?id_tmdb=${id}&tipo=${tipo}`).then(setListas, () =>
      setListas([])
    );
  }, [id, tipo]);

  useEffect(() => {
    if (!conSesion) return;
    let vigente = true;
    apiFetch<MiCalificacion>(`/api/reviews/mias/?id_tmdb=${id}&tipo=${tipo}`).then(
      (datos) => vigente && setMia(datos),
      (error: unknown) => {
        if (!vigente) return;
        setMia(null);
        if (!(error instanceof ApiError && error.status === 404))
          toast.error(mensajeDeError(error));
      }
    );
    apiFetch<ListaFicha[]>(`/api/lists/?id_tmdb=${id}&tipo=${tipo}`).then(
      (datos) => vigente && setListas(datos),
      () => vigente && setListas([])
    );
    return () => {
      vigente = false;
    };
  }, [conSesion, id, tipo]);

  const listaOrigen = origen.tipo === "lista" ? origen.id : null;
  useEffect(() => {
    if (!conSesion || listaOrigen === null) return;
    let vigente = true;
    apiFetch<{ nombre: string }>(`/api/lists/${listaOrigen}/`).then(
      (lista) => vigente && setNombreLista(lista.nombre),
      () => undefined
    );
    return () => {
      vigente = false;
    };
  }, [conSesion, listaOrigen]);

  if (detalle.status === "error") {
    return (
      <main
        id="contenido"
        className="mx-auto flex max-w-[1360px] flex-col items-start gap-4 px-5 pt-28 pb-16 md:px-10"
      >
        <p role="alert" className="text-fg-2">
          {mensajeDeError(detalle.error)}
        </p>
        <button
          type="button"
          onClick={() => setIntento((anterior) => anterior + 1)}
          className="inline-flex h-12 cursor-pointer items-center rounded-lg bg-raised-2 px-[22px] font-semibold focus-visible:outline-2 focus-visible:outline-ring"
        >
          {t("common.actions.retry")}
        </button>
      </main>
    );
  }

  const ficha = detalle.data ? normalizarFicha(detalle.data, tipo) : null;
  const miga = [
    ...(origen.tipo === "search"
      ? [{ label: t("nav.main.search"), href: routes.search }]
      : origen.tipo === "reviews"
        ? [
            { label: t("nav.main.profileShort"), href: routes.profile },
            { label: t("nav.main.ratingsReviews"), href: routes.myReviews },
          ]
        : origen.tipo === "lista"
          ? [
              { label: t("nav.main.lists"), href: routes.lists },
              ...(nombreLista ? [{ label: nombreLista, href: routes.list(origen.id) }] : []),
            ]
          : [{ label: t("nav.main.home"), href: routes.explore }]),
  ];
  const volver = miga[miga.length - 1];
  const enVistas = listas?.find((lista) => lista.clave === "vistas")?.contiene ?? false;

  async function guardar({ valor, texto }: { valor: number; texto: string }) {
    if (!mia) {
      const nueva = await apiFetch<MiCalificacion>("/api/reviews/", {
        method: "POST",
        body: { id_tmdb: id, tipo, valor, ...(texto ? { texto } : {}) },
      });
      setMia(nueva);
      toast.success(
        t(texto ? "title.feedback.ratingReviewPublished" : "title.feedback.ratingPublished")
      );
    } else {
      const plan = planEdicion(mia, valor, texto);
      let actual: MiCalificacion = mia;
      if (plan.borrarTexto) {
        await apiFetch(`/api/reviews/${mia.id}/texto/`, { method: "DELETE" });
        actual = { ...actual, texto: null };
      }
      if (Object.keys(plan.cambios).length) {
        actual = await apiFetch<MiCalificacion>(`/api/reviews/${mia.id}/`, {
          method: "PUT",
          body: plan.cambios,
        });
      }
      setMia(actual);
      const nota = "valor" in plan.cambios;
      const textoCambio = "texto" in plan.cambios || plan.borrarTexto;
      if (nota && textoCambio) toast.success(t("title.feedback.ratingReviewUpdated"));
      else if (nota) toast.success(t("title.feedback.ratingUpdated"));
      else if (plan.borrarTexto) toast.success(t("title.feedback.reviewDeleted"));
      else if (textoCambio) toast.success(t("title.feedback.reviewUpdated"));
    }
    setModal(null);
    // Calificar suma a Vistas en el servidor: las listas traen el `item_id` nuevo.
    await recargarListas();
  }

  async function quitarCalificacion() {
    if (!mia) return;
    await apiFetch(`/api/reviews/${mia.id}/`, { method: "DELETE" });
    toast.success(
      t(mia.texto ? "title.feedback.ratingReviewDeleted" : "title.feedback.ratingDeleted")
    );
    setMia(null);
    setModal(null);
    await recargarListas();
  }

  const cargandoUsuario = conSesion && (mia === undefined || listas === null);
  const larga = (ficha?.sinopsis.length ?? 0) > 300;

  return (
    <main id="contenido" className="pb-16">
      {/* Franja de fondo: la barra de navegación va encima (Navbar.tsx). */}
      <div className="relative h-[280px] overflow-hidden md:h-[620px]">
        {ficha?.backdrop ? (
          <Image
            unoptimized
            priority
            fill
            sizes="100vw"
            src={ficha.backdrop}
            alt=""
            className="object-cover object-[50%_30%]"
          />
        ) : (
          <div className="absolute inset-0 bg-raised" />
        )}
        <div
          aria-hidden="true"
          className="absolute inset-0 md:hidden"
          style={{ background: VELO_CELULAR }}
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 hidden md:block"
          style={{ background: VELO_ESCRITORIO }}
        />
        <Link
          href={volver.href}
          aria-label={t("title.breadcrumb.backTo", { label: volver.label })}
          className="relative mt-[60px] ml-4 inline-flex h-10 items-center gap-1 rounded-full bg-[rgb(var(--scrim)/0.6)] pr-3.5 pl-2 text-[15px] font-medium text-foreground no-underline backdrop-blur-sm md:hidden"
        >
          <ChevronLeft aria-hidden="true" className="size-5" />
          {volver.label}
        </Link>
      </div>

      <div className="relative mx-auto -mt-24 flex max-w-[1360px] flex-col gap-16 px-5 md:-mt-[380px] md:gap-24 md:px-10">
        <div className="grid grid-cols-[116px_minmax(0,1fr)] items-end gap-x-4 gap-y-6 md:grid-cols-[300px_minmax(0,1fr)] md:items-start md:gap-x-14">
          <div className="relative aspect-[2/3] overflow-hidden rounded-[10px] bg-raised shadow-[0_14px_34px_rgb(0_0_0/0.5)] md:row-span-2 md:rounded-xl md:shadow-[0_24px_60px_rgb(0_0_0/0.5)]">
            {ficha?.poster && (
              <Image
                unoptimized
                fill
                sizes="(min-width: 768px) 300px, 116px"
                src={ficha.poster}
                alt={t("common.media.posterAlt", { title: ficha.titulo })}
                className="object-cover"
              />
            )}
          </div>

          <div className="flex min-w-0 flex-col gap-1.5 pb-1 md:gap-5 md:pt-7 md:pb-0">
            <nav
              aria-label={t("nav.main.breadcrumbLabel")}
              className="hidden text-sm text-fg-2 md:block"
            >
              <ol className="flex flex-wrap items-center gap-2">
                {miga.map((tramo) => (
                  <li key={tramo.href} className="flex items-center gap-2">
                    <Link href={tramo.href} className="text-fg-2 hover:text-foreground">
                      {tramo.label}
                    </Link>
                    <span aria-hidden="true">›</span>
                  </li>
                ))}
                <li aria-current="page" className="font-semibold text-foreground">
                  {ficha?.titulo}
                </li>
              </ol>
            </nav>
            {ficha ? (
              <>
                <div className="flex flex-col gap-2.5">
                  <h1
                    lang={ficha.tituloEnIngles ? "en" : undefined}
                    className={cn(
                      "mb-[15px] font-display text-balance break-words",
                      TAMANIO_TITULO[tamanioTitulo(ficha.titulo)],
                      "leading-[0.9]"
                    )}
                  >
                    {ficha.titulo}
                  </h1>
                  {ficha.lema && (
                    <p className="hidden text-lg text-fg-2 italic md:block">{ficha.lema}</p>
                  )}
                </div>
                <p className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-sm text-fg-2 md:gap-x-3.5 md:text-[15px]">
                  <span className="font-semibold text-foreground">
                    {t(tipo === "movie" ? "common.content.movie" : "common.content.tvShow")}
                  </span>
                  {ficha.anio && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>{ficha.anio}</span>
                    </>
                  )}
                  {ficha.duracion && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>{formats.duration(ficha.duracion)}</span>
                    </>
                  )}
                  {(ficha.temporadas || ficha.episodios) && (
                    // En celular, temporadas y episodios van en su propio renglón
                    // para que ningún «·» quede colgando al final de una línea.
                    <span className="flex basis-full items-center gap-x-2.5 md:basis-auto md:gap-x-3.5">
                      <span aria-hidden="true" className="hidden md:inline">
                        ·
                      </span>
                      {ficha.temporadas && (
                        <span>{t("title.metadata.seasons", { count: ficha.temporadas })}</span>
                      )}
                      {ficha.temporadas && ficha.episodios && <span aria-hidden="true">·</span>}
                      {ficha.episodios && (
                        <span>{t("title.metadata.episodes", { count: ficha.episodios })}</span>
                      )}
                    </span>
                  )}
                  {ficha.nota !== null && (
                    <>
                      <span aria-hidden="true" className="hidden md:inline">
                        ·
                      </span>
                      {/* En celular la nota baja a su propio renglón (canvas). */}
                      <span className="inline-flex basis-full items-center gap-1.5 md:basis-auto">
                        <span className="sr-only">
                          {t("title.metadata.ratingVotesLabel", {
                            rating: formats.rating(ficha.nota),
                            count: ficha.votos,
                          })}
                        </span>
                        <svg
                          aria-hidden="true"
                          viewBox="0 0 24 24"
                          className="size-[15px] fill-primary"
                        >
                          <polygon points={ESTRELLA} />
                        </svg>
                        <span aria-hidden="true" className="font-semibold text-foreground">
                          {formats.rating(ficha.nota)}
                        </span>
                        <span aria-hidden="true">
                          {t("title.metadata.voteCount", { count: ficha.votos })}
                        </span>
                      </span>
                    </>
                  )}
                </p>
              </>
            ) : (
              <div aria-hidden="true" className="flex flex-col gap-3">
                <span className="h-12 w-2/3 animate-pulse rounded bg-raised md:h-24" />
                <span className="h-4 w-1/2 animate-pulse rounded bg-raised" />
              </div>
            )}
          </div>

          <div className="col-span-2 flex min-w-0 flex-col gap-8 md:col-span-1 md:col-start-2 md:gap-6">
            {cargando || cargandoUsuario ? (
              <span
                aria-hidden="true"
                className="h-12 w-full animate-pulse rounded-lg bg-raised md:w-[520px]"
              />
            ) : conSesion && listas && ficha ? (
              <TitleActions
                titulo={ficha.titulo}
                idTmdb={id}
                tipo={tipo}
                listas={listas}
                onListasChange={setListas}
                miCalificacion={mia ?? null}
                onRate={() => setModal("calificar")}
                onCalificacionBorrada={() => setMia(null)}
              />
            ) : (
              <Link
                href={`${routes.login}?next=${encodeURIComponent(pathname)}`}
                className="inline-flex h-12 items-center justify-center self-stretch rounded-lg bg-primary px-[22px] font-semibold text-primary-foreground no-underline md:self-start"
              >
                {t("title.actions.signedOutPrompt")}
              </Link>
            )}
            {ficha && ficha.generos.length > 0 && (
              <ul aria-label={t("title.metadata.genresTitle")} className="flex flex-wrap gap-2">
                {ficha.generos.map((genero) => (
                  <li
                    key={genero}
                    className="inline-flex h-[30px] items-center rounded-full px-3 text-[13px] text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] md:h-8 md:text-sm"
                  >
                    {genero}
                  </li>
                ))}
              </ul>
            )}
            {ficha?.sinopsis && (
              <div className="flex flex-col gap-2 md:max-w-[720px]">
                <h2 className="text-[13px] font-semibold text-fg-3">
                  {t("title.synopsis.heading")}
                </h2>
                <p
                  lang={ficha.sinopsisEnIngles ? "en" : undefined}
                  className={cn(
                    "text-[17px] leading-[1.6] text-pretty",
                    larga && !sinopsisCompleta && "line-clamp-5"
                  )}
                >
                  {ficha.sinopsis}
                </p>
                {larga && (
                  <button
                    type="button"
                    aria-expanded={sinopsisCompleta}
                    onClick={() => setSinopsisCompleta(!sinopsisCompleta)}
                    className="h-11 cursor-pointer self-start font-semibold text-fg-2 hover:text-foreground"
                  >
                    {sinopsisCompleta ? t("common.text.readLess") : t("common.text.readMore")}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {creditos.data && <CreditsSection creditos={creditos.data} tipo={tipo} />}
      </div>

      {modal === "calificar" && ficha && (
        <RatingDialog
          titulo={ficha.titulo}
          enVistas={enVistas}
          inicial={mia ? { valor: mia.valor, texto: mia.texto } : undefined}
          onSubmit={guardar}
          onRemoveRating={() => setModal("quitar")}
          onClose={() => setModal(null)}
        />
      )}
      {modal === "quitar" && ficha && mia && (
        <ConfirmDialog
          titulo={t("title.rating.removeConfirmTitle")}
          descripcion={t(
            mia.texto ? "title.rating.removeBothDescription" : "title.rating.removeOnlyDescription",
            { title: ficha.titulo }
          )}
          preview={mia.texto}
          confirmar={t("common.rating.remove")}
          onConfirm={quitarCalificacion}
          onCancel={() => setModal(null)}
        />
      )}
    </main>
  );
}
