"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { MessageCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount } from "@/components/AccountProvider";
import { HomeHero } from "@/components/features/HomeHero";
import { MediaRow } from "@/components/features/MediaRow";
import { TypeSelector, type ContentType } from "@/components/features/TypeSelector";
import { ApiError } from "@/lib/api";
import { normalizeTitles, type TmdbItem } from "@/lib/catalog";
import { translateError } from "@/lib/errors";
import { useFormats } from "@/lib/format";
import { alternar, elegirHero, tipoDesdeUrl } from "@/lib/home";
import { routes } from "@/lib/routes";
import { useCatalog, type Pedido } from "@/lib/use-catalog";

type Lista = { results: TmdbItem[] };
type Recomendado = { generos: string[]; results: TmdbItem[] };
type Generos = { genres: { id: number; name: string }[] };

/** Una página de TMDB por fila (doc 04 §5, 13/10/2026); Recomendado trae hasta 15. */
const POR_FILA = 20;
/** Series del año con al menos 50 votos (verificado contra TMDB el 13/10/2026). */
const MIN_VOTOS_SERIES = 50;

function mensaje(error: unknown) {
  return error instanceof ApiError ? error.message : translateError({ code: "unknown" });
}

/**
 * Home de descubrimiento (C-05). Cada fila pide sus datos por separado: si una
 * falla, se oculta y un único aviso lo cuenta; si fallan todas, hay un mensaje
 * con «Reintentar». El selector vive en la URL (`?type=movie|tv`).
 */
export function HomeView() {
  const t = useTranslations("home");
  const tc = useTranslations("common");
  const tn = useTranslations("nav.account");
  const tf = useTranslations("footer.main");
  const tipo = tipoDesdeUrl(useSearchParams().get("type"));
  const { perfil, cargando } = useAccount();
  const conSesion = !cargando && perfil !== null;
  const formats = useFormats();
  const [intento, setIntento] = useState(0);
  const anio = new Date().getFullYear();
  const invitacionId = useId();

  const tendenciasAll = useCatalog<Lista>("/api/catalogo/trending/?media_type=all", intento);
  const tendenciasTipo = useCatalog<Lista>(
    tipo === "all" ? null : `/api/catalogo/trending/?media_type=${tipo}`,
    intento
  );
  const enCines = useCatalog<Lista>(tipo === "tv" ? null : "/api/catalogo/now-playing/", intento);
  const seriesDelAnio = useCatalog<Lista>(
    tipo === "movie"
      ? null
      : `/api/catalogo/discover/?tipo=tv&anio=${anio}&min_votes=${MIN_VOTOS_SERIES}`,
    intento
  );
  const recomendado = useCatalog<Recomendado>(
    conSesion ? `/api/catalogo/recommended/?tipo=${tipo}` : null,
    intento,
    false
  );
  const generosPeliculas = useCatalog<Generos>("/api/catalogo/genres/?tipo=movie", intento);
  const generosSeries = useCatalog<Generos>("/api/catalogo/genres/?tipo=tv", intento);

  const tendencias = tipo === "all" ? tendenciasAll : tendenciasTipo;
  const titulosTendencia = normalizeTitles(
    tendencias.data?.results ?? [],
    tipo === "all" ? undefined : tipo
  );
  const heroAll = elegirHero(normalizeTitles(tendenciasAll.data?.results ?? []));
  const hero = tipo === "all" ? heroAll : elegirHero(titulosTendencia, heroAll?.titulo);
  const nombres = new Map(
    (hero?.titulo.tipo === "tv" ? generosSeries : generosPeliculas).data?.genres.map((g) => [
      g.id,
      g.name,
    ]) ?? []
  );
  const generosHero = (hero?.titulo.generoIds ?? []).flatMap((id) => nombres.get(id) ?? []);

  const peliculasNuevas = normalizeTitles(enCines.data?.results ?? [], "movie");
  const seriesNuevas = normalizeTitles(seriesDelAnio.data?.results ?? [], "tv");
  const novedades =
    tipo === "all"
      ? alternar(peliculasNuevas, seriesNuevas, POR_FILA)
      : tipo === "movie"
        ? peliculasNuevas
        : seriesNuevas;
  const recomendados = normalizeTitles(recomendado.data?.results ?? []);
  const generosRecomendados = recomendado.data?.generos ?? [];

  // Una fila cuenta como pedida si no está apagada (`idle`).
  const pedidos: Pedido<unknown>[] = [tendencias, enCines, seriesDelAnio, recomendado].filter(
    (pedido) => pedido.status !== "idle"
  );
  const fallidos = pedidos.filter((pedido) => pedido.status === "error");
  const todoFalla = pedidos.length > 0 && fallidos.length === pedidos.length;
  // El aviso de «algo no cargó» espera a que terminen todos los pedidos: si no,
  // cuando fallan todos salía primero el toast y después el mismo error en la
  // página (Q-03, 16/10/2026).
  const terminados = pedidos.every((pedido) => pedido.status !== "loading");
  const avisoParcial =
    terminados && fallidos.length > 0 && !todoFalla ? mensaje(fallidos[0].error) : null;
  // Todas las filas llegaron bien pero sin títulos: sin esto la página quedaba
  // en blanco, sin explicación ni salida.
  const todoVacio =
    terminados &&
    fallidos.length === 0 &&
    pedidos.length > 0 &&
    titulosTendencia.length === 0 &&
    novedades.length === 0 &&
    recomendados.length === 0;

  useEffect(() => {
    if (avisoParcial) toast.error(avisoParcial, { id: "home-carga" });
  }, [avisoParcial]);

  function elegirTipo(nuevo: ContentType) {
    // History API del navegador y no `router.replace`: Next.js lo sincroniza con
    // `useSearchParams` sin volver a pedir la página al servidor, así el cambio
    // es inmediato.
    window.history.replaceState(
      null,
      "",
      nuevo === "all" ? routes.explore : `${routes.explore}?type=${nuevo}`
    );
  }

  const razon =
    tipo === "all"
      ? "rows.recommendationReasonCombined"
      : tipo === "movie"
        ? "rows.recommendationReasonMovies"
        : "rows.recommendationReasonTv";
  const descripcionNovedades =
    tipo === "all"
      ? t("rows.newReleasesDescription")
      : tipo === "movie"
        ? t("rows.inCinemasTitle")
        : t("rows.tvPremieresTitle", { year: String(anio) });

  return (
    <main id="contenido" className="pb-6 md:pb-0">
      <HomeHero
        hero={hero}
        cargando={tendencias.status === "loading" || tendenciasAll.status === "loading"}
        tipo={tipo}
        generos={generosHero}
        selector={
          <TypeSelector
            value={tipo}
            onChange={elegirTipo}
            className="md:bg-[rgb(var(--scrim)/0.72)]"
          />
        }
      />
      {todoFalla ? (
        <div className="mx-auto flex max-w-[1360px] flex-col items-start gap-4 px-5 py-16 md:px-10">
          <p role="alert" className="text-fg-2">
            {mensaje(fallidos[0].error)}
          </p>
          <button
            type="button"
            onClick={() => setIntento((anterior) => anterior + 1)}
            className="inline-flex h-12 cursor-pointer items-center rounded-lg bg-raised-2 px-[22px] font-semibold focus-visible:outline-2 focus-visible:outline-ring"
          >
            {tc("actions.retry")}
          </button>
        </div>
      ) : todoVacio ? (
        <div className="mx-auto flex max-w-[1360px] flex-col items-start gap-4 px-5 py-16 md:px-10">
          <p role="status" className="max-w-[60ch] text-fg-2">
            {t("rows.emptyDescription")}
          </p>
          <Link
            href={routes.search}
            className="inline-flex h-12 items-center rounded-lg bg-raised-2 px-[22px] font-semibold text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring"
          >
            {tc("actions.explore")}
          </Link>
        </div>
      ) : (
        <div className="mx-auto flex max-w-[1360px] flex-col gap-11 pt-7 pb-12 md:gap-20 md:px-10 md:pt-10 md:pb-20">
          {conSesion && (
            <MediaRow
              title={t("rows.recommendedTitle")}
              description={
                generosRecomendados.length > 0
                  ? t(razon, { genres: formats.list(generosRecomendados) })
                  : undefined
              }
              items={recomendados}
              showType={tipo === "all"}
              from="home"
              loading={recomendado.status === "loading"}
            />
          )}
          <MediaRow
            title={t("rows.trendingTitle")}
            description={t("rows.trendingDescription")}
            items={titulosTendencia.slice(0, POR_FILA)}
            showType={tipo === "all"}
            from="home"
            loading={tendencias.status === "loading"}
          />
          <MediaRow
            title={t("rows.newReleasesTitle")}
            description={descripcionNovedades}
            items={novedades}
            showType={tipo === "all"}
            from="home"
            loading={enCines.status === "loading" || seriesDelAnio.status === "loading"}
          />
          {!cargando && !perfil && (
            <section
              aria-labelledby={invitacionId}
              className="mx-5 flex flex-wrap items-center gap-x-12 gap-y-6 border-y border-line py-10 md:mx-0"
            >
              <div className="flex flex-[1_1_480px] flex-col gap-1.5">
                <h2 id={invitacionId} className="font-display text-[40px] leading-none">
                  {t("guest.title")}
                </h2>
                <p className="max-w-[560px] text-pretty text-fg-2">{t("guest.description")}</p>
              </div>
              <div className="flex gap-3">
                <Link
                  href={routes.register}
                  className="inline-flex h-12 items-center rounded-lg bg-raised-2 px-[22px] font-semibold text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring"
                >
                  {tn("signUp")}
                </Link>
                <Link
                  href={routes.login}
                  className="inline-flex h-12 items-center px-3 font-medium text-fg-2 no-underline hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
                >
                  {t("guest.loginAction")}
                </Link>
              </div>
            </section>
          )}
        </div>
      )}
      {conSesion && (
        // Provisorio: el chatbot (B-04) todavía no existe y `/chat` responde 404 (Not Found).
        // Sin prefetch hasta entonces: cada página pedía ese 404 de fondo.
        <Link
          href={routes.askFilmAI}
          prefetch={false}
          className="fixed right-4 bottom-[92px] z-30 grid size-14 place-items-center rounded-full bg-primary font-semibold text-primary-foreground no-underline shadow-[0_10px_24px_rgb(0_0_0/0.4)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:right-8 md:bottom-8 md:inline-flex md:w-auto md:gap-2.5 md:pr-[22px] md:pl-[18px]"
        >
          <MessageCircle aria-hidden="true" className="size-6" />
          <span className="sr-only md:not-sr-only">{tf("askFilmAI")}</span>
        </Link>
      )}
    </main>
  );
}
