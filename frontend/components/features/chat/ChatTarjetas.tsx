"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import { useChat } from "@/components/ChatProvider";
import { UnavailableCard } from "@/components/features/UnavailableCard";
import { StarIcon } from "@/components/ui/StarIcon";
import { tmdbImage } from "@/lib/catalog";
import type { Tarjeta } from "@/lib/chat";
import { useFormats } from "@/lib/format";
import { routes } from "@/lib/routes";

/**
 * Hasta tres producciones recomendadas. El link lo arma el front con
 * `id_tmdb` y `tipo` (nunca una URL escrita por el modelo) y lleva
 * `?from=chat`. Toda la fila es el link: un control por tarjeta. Al elegir
 * una, el panel se cierra para que se vea la ficha; la conversación sigue en
 * el provider y vuelve a aparecer al abrirlo.
 */
export function ChatTarjetas({ tarjetas }: { tarjetas: Tarjeta[] }) {
  const t = useTranslations("common");
  const formats = useFormats();
  const { cerrar } = useChat();
  if (!tarjetas.length) return null;
  return (
    <ul className="m-0 flex list-none flex-col p-0">
      {tarjetas.map((tarjeta) => {
        if (tarjeta.titulo === null) {
          // TMDB ya no tiene el título: nada a lo que enlazar (#180).
          return (
            <li key={`${tarjeta.tipo}-${tarjeta.id_tmdb}`} className="border-t border-line">
              <UnavailableCard compact />
            </li>
          );
        }
        const poster = tmdbImage(tarjeta.poster, "w185");
        const tipo = t(tarjeta.tipo === "movie" ? "content.movie" : "content.tvShow");
        return (
          <li key={`${tarjeta.tipo}-${tarjeta.id_tmdb}`} className="border-t border-line">
            <Link
              href={routes.title(tarjeta.tipo, tarjeta.id_tmdb, "chat")}
              onClick={cerrar}
              className="grid grid-cols-[2.75rem_minmax(0,1fr)] items-center gap-3 rounded-md py-2 text-foreground no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:grid-cols-[3rem_minmax(0,1fr)_auto] md:gap-3.5 md:py-2.5"
            >
              {poster ? (
                // Decorativo: el título ya está escrito al lado (canvas).
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={poster}
                  alt=""
                  loading="lazy"
                  className="aspect-[2/3] w-full rounded-md bg-raised-2 object-cover"
                />
              ) : (
                <span aria-hidden="true" className="aspect-[2/3] w-full rounded-md bg-raised-2" />
              )}
              <span className="flex min-w-0 flex-col">
                <span className="truncate font-semibold">{tarjeta.titulo}</span>
                <span className="flex items-center gap-1.5 text-[0.8125rem] text-fg-3">
                  <span className="whitespace-nowrap">
                    {tipo}
                    {tarjeta.anio && " · "}
                    {tarjeta.anio}
                  </span>
                  {typeof tarjeta.nota_tmdb === "number" && (
                    <span className="inline-flex items-center gap-1 text-fg-2">
                      <span className="sr-only">
                        {t("media.tmdbRatingLabel", { rating: formats.rating(tarjeta.nota_tmdb) })}
                      </span>
                      <StarIcon className="size-[0.6875rem] fill-primary" />
                      <span aria-hidden="true">{formats.rating(tarjeta.nota_tmdb)}</span>
                    </span>
                  )}
                </span>
              </span>
              <span
                aria-hidden="true"
                className="hidden h-10 items-center rounded-lg px-2.5 text-sm font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] md:inline-flex"
              >
                {t("media.viewDetails")}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
