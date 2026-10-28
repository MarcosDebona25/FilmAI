"use client";

import type { ReactNode } from "react";
import Image from "next/image";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";

import type { ContentType } from "@/components/features/TypeSelector";
import { StarIcon } from "@/components/ui/StarIcon";
import { tmdbLoader, type Title } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import { tamanioTitulo } from "@/lib/home";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

// Velos del canvas: en celular solo abajo y arriba; en escritorio también de
// izquierda a derecha, para que el texto se lea sobre cualquier imagen.
const VELO_CELULAR =
  "linear-gradient(0deg, rgb(var(--scrim)) 0%, rgb(var(--scrim) / 0.9) 32%, rgb(var(--scrim) / 0) 62%), linear-gradient(180deg, rgb(var(--scrim)) 0%, rgb(var(--scrim) / 0) 14%)";
// Clases enteras (no armadas por partes) para que Tailwind las genere.
const TAMANIO_TITULO = {
  grande: "text-[72px] md:text-[152px]",
  mediano: "text-[56px] md:text-[112px]",
  chico: "text-[44px] md:text-[88px]",
} as const;
const VELO_ESCRITORIO =
  "linear-gradient(90deg, rgb(var(--scrim)) 0%, rgb(var(--scrim) / 0.92) 28%, rgb(var(--scrim) / 0.25) 58%, rgb(var(--scrim) / 0) 74%), linear-gradient(0deg, rgb(var(--scrim)) 0%, rgb(var(--scrim) / 0) 34%), linear-gradient(180deg, rgb(var(--scrim) / 0.75) 0%, rgb(var(--scrim) / 0) 22%)";

/**
 * Hero del Home. En escritorio ocupa la parte de arriba de la pantalla, con la
 * barra de navegación y el selector encima de la imagen; en celular el
 * selector va arriba y la imagen debajo.
 */
export function HomeHero({
  hero,
  cargando,
  tipo,
  generos,
  selector,
}: {
  hero: { titulo: Title; puesto: number } | null;
  cargando: boolean;
  tipo: ContentType;
  generos: string[];
  selector: ReactNode;
}) {
  const t = useTranslations();
  const formats = useFormats();
  const titulo = hero?.titulo ?? null;
  const conImagen = cargando || titulo !== null;
  // El `<h1>` visible es el título del Hero y solo existe con imagen. Sin ella
  // (cargando, sin destacado o sin fondo) el Inicio no puede quedarse sin `<h1>`.
  const sinTituloVisible = cargando || !titulo?.backdrop;

  return (
    <section
      aria-labelledby="hero-titulo"
      className={cn("relative flex flex-col", conImagen && "md:min-h-[720px] md:overflow-hidden")}
    >
      {sinTituloVisible && (
        <h1 id="hero-titulo" className="sr-only">
          {t("nav.main.home")}
        </h1>
      )}
      <div className="relative z-10 px-5 pt-1 pb-4 md:mx-auto md:w-full md:max-w-[1360px] md:px-10 md:pt-[88px] md:pb-0">
        {selector}
      </div>
      {/*
        «Escenario» del Hero: solo la imagen es `absolute`; el texto va en el flujo
        y se empuja hacia abajo. Un título largo agranda la sección en lugar de
        subirse encima del selector. En celular la imagen cubre el escenario (debajo
        del selector); en escritorio el escenario es `static`, así que la imagen
        cubre toda la sección, también detrás de la barra y del selector.
      */}
      {cargando ? (
        <div className="relative min-h-[560px] flex-1 md:static md:min-h-0">
          <div className="absolute inset-0 bg-raised" />
        </div>
      ) : (
        titulo?.backdrop && (
          <div className="relative flex min-h-[560px] flex-1 flex-col justify-end md:static md:min-h-0 md:pt-12">
            <div aria-hidden="true" className="absolute inset-0 overflow-hidden">
              <Image
                loader={tmdbLoader}
                // `priority` solo precarga y quita el lazy; sin `fetchPriority` el
                // navegador pedía esta imagen (el LCP) con prioridad baja.
                priority
                fetchPriority="high"
                fill
                sizes="100vw"
                src={titulo.backdrop}
                alt=""
                className="object-cover object-[50%_35%]"
              />
              <div className="absolute inset-0 md:hidden" style={{ background: VELO_CELULAR }} />
              <div
                className="absolute inset-0 hidden md:block"
                style={{ background: VELO_ESCRITORIO }}
              />
            </div>
            <div className="relative flex flex-col gap-3 px-5 pb-7 md:mx-auto md:w-full md:max-w-[1360px] md:gap-[18px] md:px-10 md:pb-[72px]">
              <p className="flex gap-2 text-sm text-fg-2 md:gap-2.5 md:text-[15px]">
                <span className="font-semibold text-primary">
                  {tipo === "all"
                    ? t("home.hero.trendingRank", { rank: String(hero!.puesto) })
                    : t("home.hero.weeklyHighlight")}
                </span>
                <span aria-hidden="true">·</span>
                <span>
                  {t(titulo.tipo === "movie" ? "common.content.movie" : "common.content.tvShow")}
                </span>
              </p>
              <h1
                id="hero-titulo"
                lang={titulo.tituloEnIngles ? "en" : undefined}
                className={cn(
                  "mb-[15px] font-display text-balance",
                  TAMANIO_TITULO[tamanioTitulo(titulo.titulo)],
                  // Al final: `tailwind-merge` borra un `leading-*` que venga antes
                  // de una clase de tamaño de letra.
                  "leading-[0.9]"
                )}
              >
                {titulo.titulo}
              </h1>
              <p className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-sm text-fg-2 md:gap-3 md:text-[15px]">
                {titulo.anio && <span>{titulo.anio}</span>}
                {generos.length > 0 && (
                  // En celular los géneros bajan a su propio renglón (`order-last`,
                  // ancho completo) para que ningún «·» quede colgando al partirse.
                  <>
                    <span aria-hidden="true" className="hidden md:inline">
                      ·
                    </span>
                    <span className="order-last basis-full md:order-none md:basis-auto">
                      {generos.join(", ")}
                    </span>
                  </>
                )}
                {titulo.nota !== null && (
                  <>
                    <span aria-hidden="true">·</span>
                    <span className="inline-flex items-center gap-1.5 font-semibold text-foreground">
                      <span className="sr-only">
                        {t("home.hero.tmdbRatingLabel", { rating: formats.rating(titulo.nota) })}
                      </span>
                      <StarIcon className="size-[13px] fill-primary" />
                      <span aria-hidden="true">{formats.rating(titulo.nota)}</span>
                    </span>
                  </>
                )}
              </p>
              {titulo.sinopsis && (
                <p
                  lang={titulo.sinopsisEnIngles ? "en" : undefined}
                  className="hidden max-w-[520px] text-[17px] leading-[1.6] text-pretty text-fg-2 md:line-clamp-3"
                >
                  {titulo.sinopsis}
                </p>
              )}
              <Link
                href={routes.title(titulo.tipo, titulo.id, "home")}
                className="mt-1.5 flex h-[52px] items-center justify-center gap-2 rounded-lg bg-primary px-6 font-semibold text-primary-foreground no-underline hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:mt-2 md:inline-flex md:h-12 md:self-start md:pr-[22px]"
              >
                {t("common.media.viewDetails")}
                <ArrowRight aria-hidden="true" className="hidden size-[18px] md:block" />
              </Link>
            </div>
          </div>
        )
      )}
    </section>
  );
}
