"use client";

import { useState } from "react";
import { ListPlus } from "lucide-react";
import { getImageProps } from "next/image";

import Link from "next/link";
import { useTranslations } from "next-intl";

import { StarIcon } from "@/components/ui/StarIcon";
import { tmdbConTope, tmdbLoader, type Title } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

/**
 * Ancho de la tarjeta desde `md` (fila o grilla con `--cols` columnas, margen
 * del contenedor y gap de 20 px), para que el navegador baje el póster justo.
 * Desde 1440 px la raíz crece y la tarjeta llega a ~224 px.
 */
const SIZES_ESCRITORIO =
  "(min-width: 1440px) 224px, (min-width: 1280px) calc(16.67vw - 30px), (min-width: 1024px) calc(20vw - 32px), calc(25vw - 35px)";

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
  /** En una grilla (Search, L-03) ocupa su columna también en celular (fila: 132 px). */
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
        fluid ? "w-full" : "w-[8.25rem] md:w-full"
      )}
    >
      <span className="relative block aspect-[2/3] overflow-hidden rounded-lg bg-raised transition-[transform,box-shadow] duration-200 group-hover:-translate-y-1 group-hover:shadow-[0_14px_30px_rgb(0_0_0/0.45)] group-focus-visible:outline-2 group-focus-visible:outline-offset-[3px] group-focus-visible:outline-ring motion-reduce:transition-none motion-reduce:group-hover:translate-y-0">
        {poster ? (
          <Poster
            src={poster}
            alt={t("media.posterAlt", { title: title.titulo })}
            sizesCelular={fluid ? "50vw" : "132px"}
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
          className="truncate text-sm font-semibold md:text-[0.9375rem]"
        >
          {title.titulo}
        </span>
        <span className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs text-fg-3 md:gap-x-2 md:text-[0.8125rem]">
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
              <StarIcon className="size-[0.6875rem] fill-primary md:size-3" />
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
            className="inline-flex items-center gap-1 text-[0.6875rem] text-fg-3 tabular-nums"
          >
            <ListPlus className="size-[0.6875rem]" aria-hidden="true" />
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

/**
 * Póster con dos juegos de anchos: en celular el de siempre (tope `w342`, mismo
 * peso que antes) y desde `md` hasta `w500`, para que la tarjeta de ~224 px de
 * las pantallas anchas no se vea borrosa con densidad 2. `getImageProps` arma
 * los `srcset` de `next/image` para un `<picture>` (dirección de arte).
 */
function Poster({
  src,
  alt,
  sizesCelular,
  onError,
}: {
  src: string;
  alt: string;
  sizesCelular: string;
  onError: () => void;
}) {
  const comun = { alt, fill: true, loader: tmdbLoader, className: "object-cover" };
  const {
    props: { srcSet: srcSetEscritorio, sizes: sizesEscritorio },
  } = getImageProps({ ...comun, src: tmdbConTope(src, "w500"), sizes: SIZES_ESCRITORIO });
  const { props: celular } = getImageProps({
    ...comun,
    src: tmdbConTope(src, "w342"),
    sizes: sizesCelular,
  });
  return (
    <picture>
      <source media="(min-width: 768px)" srcSet={srcSetEscritorio} sizes={sizesEscritorio} />
      {/* eslint-disable-next-line jsx-a11y/alt-text -- el alt llega en las props de getImageProps */}
      <img {...celular} onError={onError} />
    </picture>
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
