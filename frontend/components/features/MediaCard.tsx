"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { Title } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import { routes } from "@/lib/routes";

/**
 * Tarjeta de un título: póster 2:3, nombre y una línea con tipo, año y nota de
 * TMDB. Lleva a la ficha (C-07). La usan las filas del Home y, después, Search
 * y el detalle de listas (L-03).
 */
export function MediaCard({
  title,
  showType,
  from,
}: {
  title: Title;
  showType: boolean;
  /** Origen para la miga de pan de la ficha (`home`, `search`, `list-{id}`…). */
  from?: string;
}) {
  const t = useTranslations("common");
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
      className="group relative flex w-[132px] flex-col gap-2.5 text-foreground no-underline focus-visible:outline-none md:w-[176px] md:gap-3"
    >
      <span className="relative block aspect-[2/3] overflow-hidden rounded-lg bg-raised transition-[transform,box-shadow] duration-200 group-hover:-translate-y-1 group-hover:shadow-[0_14px_30px_rgb(0_0_0/0.45)] group-focus-visible:outline-2 group-focus-visible:outline-offset-[3px] group-focus-visible:outline-ring motion-reduce:transition-none motion-reduce:group-hover:translate-y-0">
        {poster ? (
          <Image
            unoptimized
            src={poster}
            alt={t("media.posterAlt", { title: title.titulo })}
            fill
            sizes="(min-width: 768px) 176px, 132px"
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
        <span className="flex items-center gap-1.5 text-xs text-fg-3 md:gap-2 md:text-[13px]">
          {(showType || title.anio) && (
            <span>
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
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="size-[11px] fill-primary md:size-3"
              >
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              <span aria-hidden="true">{formats.rating(title.nota)}</span>
            </span>
          )}
        </span>
      </span>
    </Link>
  );
}
