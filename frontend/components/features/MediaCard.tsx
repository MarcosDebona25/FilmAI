"use client";

import { useState } from "react";
import { ListPlus } from "lucide-react";
import Image from "next/image";

import Link from "next/link";
import { useTranslations } from "next-intl";

import { StarIcon } from "@/components/ui/StarIcon";
import { tmdbLoader, type Title } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

/**
 * Tarjeta de un título: póster 2:3, nombre y una línea con tipo, año y nota de
 * TMDB. Lleva a la ficha (C-07). La usan las filas del Home y, después, Search
 * y el detalle de listas (L-03).
 */
export function MediaCard({
  title,
  showType,
  from,
  fluid = false,
  showUnrated = false,
  addedAt,
}: {
  title: Title;
  showType: boolean;
  /** Origen para la miga de pan de la ficha (`home`, `search`, `list-{id}`…). */
  from?: string;
  /** En una grilla (Search, L-03) ocupa su columna en vez de 132/176 px. */
  fluid?: boolean;
  /** «No ratings» cuando TMDB no tiene nota (canvas de Search). */
  showUnrated?: boolean;
  /** Fecha (ISO) en que se agregó a una lista (CU-009); línea discreta bajo el título. */
  addedAt?: string;
}) {
  const t = useTranslations("common");
  const ts = useTranslations("search.results");
  const formats = useFormats();
  const [failed, setFailed] = useState<string | null>(null);
  const poster = title.poster && failed !== title.poster ? title.poster : null;
  const tipo = t(title.tipo === "movie" ? "content.movie" : "content.tvShow");

  // `relative`: la etiqueta `sr-only` de la nota es `absolute`. Sin un ancestro
  // posicionado dentro de la fila, escapa del `overflow` del `ul` y estira la
  // página hasta el ancho de todas las tarjetas.
  return (
    <Link
      href={routes.title(title.tipo, title.id, from)}
      className={cn(
        "group relative flex flex-col gap-2.5 text-foreground no-underline focus-visible:outline-none md:gap-3",
        fluid ? "w-full" : "w-[132px] md:w-[176px]"
      )}
    >
      <span className="relative block aspect-[2/3] overflow-hidden rounded-lg bg-raised transition-[transform,box-shadow] duration-200 group-hover:-translate-y-1 group-hover:shadow-[0_14px_30px_rgb(0_0_0/0.45)] group-focus-visible:outline-2 group-focus-visible:outline-offset-[3px] group-focus-visible:outline-ring motion-reduce:transition-none motion-reduce:group-hover:translate-y-0">
        {poster ? (
          <Image
            loader={tmdbLoader}
            src={poster}
            alt={t("media.posterAlt", { title: title.titulo })}
            fill
            sizes={fluid ? "(min-width: 768px) 220px, 50vw" : "(min-width: 768px) 176px, 132px"}
            className="object-cover"
            onError={() => setFailed(poster)}
          />
        ) : (
          <span className="flex h-full items-center justify-center p-3 text-center text-xs text-fg-3">
            {t("media.noPoster")}
          </span>
        )}
      </span>
      <span className="flex min-w-0 flex-col gap-px">
        <span
          lang={title.tituloEnIngles ? "en" : undefined}
          className="truncate text-sm font-semibold md:text-[15px]"
        >
          {title.titulo}
        </span>
        <span className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-fg-3 md:gap-x-2 md:text-[13px]">
          {(showType || title.anio) && (
            <span className="whitespace-nowrap">
              {showType && tipo}
              {showType && title.anio && " · "}
              {title.anio}
            </span>
          )}
          {title.nota !== null && (
            <span className="inline-flex items-center gap-1 text-fg-2">
              <span className="sr-only">
                {t("media.tmdbRatingLabel", { rating: formats.rating(title.nota) })}
              </span>
              <StarIcon className="size-[11px] fill-primary md:size-3" />
              <span aria-hidden="true">{formats.rating(title.nota)}</span>
            </span>
          )}
          {title.nota === null && showUnrated && (
            <span className="whitespace-nowrap">{ts("unrated")}</span>
          )}
        </span>
        {addedAt && (
          <time
            dateTime={addedAt}
            title={t("media.addedOnLabel", { date: formats.dateShort(addedAt) })}
            className="inline-flex items-center gap-1 text-[11px] text-fg-3 tabular-nums"
          >
            <ListPlus className="size-[11px]" aria-hidden="true" />
            <span className="sr-only">
              {t("media.addedOnLabel", { date: formats.dateShort(addedAt) })}
            </span>
            <span aria-hidden="true">{formats.dateShort(addedAt)}</span>
          </time>
        )}
      </span>
    </Link>
  );
}

/** Lugar de una `MediaCard` mientras carga la grilla (Buscar): póster y título. */
export function MediaCardSkeleton() {
  return (
    <li className="flex flex-col gap-2.5">
      <span className="block aspect-[2/3] w-full rounded-lg bg-raised" />
      <span className="h-4 w-3/4 rounded bg-raised" />
    </li>
  );
}
