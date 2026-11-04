"use client";

import { useId, useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";

import { MediaCard } from "@/components/features/MediaCard";
import type { Title } from "@/lib/catalog";
import { desplazamientoDePagina, gapDeColumnas } from "@/lib/paginado";

/** Tantos como la página más ancha (7 columnas desde 1440 px). */
const SKELETONS = 7;

/**
 * Fila con scroll horizontal del Home: título, descripción y tarjetas. En
 * celular, swipe con snap y la tarjeta siguiente asomando. Desde `md`, una
 * grilla de una sola fila con `--cols` tarjetas enteras por página (4, 5, 6 o 7
 * según el ancho, globals.css) y flechas que avanzan exactamente una página.
 * Vacía y sin cargar no se dibuja (doc 04 §5: la fila sin datos se oculta).
 */
export function MediaRow({
  title,
  description,
  items,
  showType,
  loading = false,
  from,
}: {
  title: string;
  description?: string;
  items: Title[];
  showType: boolean;
  loading?: boolean;
  from?: string;
}) {
  const t = useTranslations("home.carousel");
  const headingId = useId();
  const list = useRef<HTMLUListElement>(null);

  if (!loading && items.length === 0) return null;

  function move(direction: 1 | -1) {
    const element = list.current;
    if (!element) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    element.scrollBy({
      left: direction * desplazamientoDePagina(element.clientWidth, gapDeColumnas(element)),
      behavior: reduce ? "auto" : "smooth",
    });
  }

  const arrow =
    "grid size-11 cursor-pointer place-items-center rounded-full bg-raised text-fg-3 transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring";

  return (
    <section
      aria-labelledby={headingId}
      aria-busy={loading || undefined}
      className="flex flex-col gap-3.5 md:gap-[1.375rem]"
    >
      <div className="flex items-end justify-between gap-3 pr-3 pl-5 md:px-0">
        <div className="flex min-w-0 flex-col gap-0.5">
          <h2 id={headingId} className="font-display text-[1.875rem] leading-none md:text-[2.5rem]">
            {title}
          </h2>
          {description ? (
            <p className="text-[0.8125rem] text-fg-3 md:text-sm">{description}</p>
          ) : (
            // Mientras carga, la descripción que todavía no llegó (la de
            // Recomendado depende de la respuesta) ocupa su renglón: si no,
            // al llegar corre las tarjetas y todo lo de abajo.
            loading && (
              <p aria-hidden="true" className="invisible text-[0.8125rem] md:text-sm">
                {"\u00a0"}
              </p>
            )
          )}
        </div>
        <div className="hidden gap-2 md:flex">
          <button
            type="button"
            aria-label={t("previousRowLabel", { rowTitle: title })}
            onClick={() => move(-1)}
            className={arrow}
          >
            <ChevronLeft aria-hidden="true" className="size-5" />
          </button>
          <button
            type="button"
            aria-label={t("nextRowLabel", { rowTitle: title })}
            onClick={() => move(1)}
            className={arrow}
          >
            <ChevronRight aria-hidden="true" className="size-5" />
          </button>
        </div>
      </div>
      <ul
        ref={list}
        aria-label={t("swipeRowHint", { rowTitle: title })}
        // Desde md: `grid-auto-columns` = (100 % − (cols − 1) · gap) / cols. El
        // 1.25rem del cálculo es el `md:gap-5`: cambian juntos.
        className="flex snap-x snap-mandatory scroll-px-5 gap-3.5 overflow-x-auto overscroll-x-contain px-5 pt-1.5 pb-2.5 [scrollbar-width:none] md:grid md:scroll-px-0 md:auto-cols-[calc((100%_-_(var(--cols)_-_1)_*_1.25rem)_/_var(--cols))] md:grid-flow-col md:gap-5 md:px-0 [&::-webkit-scrollbar]:hidden"
      >
        {loading
          ? Array.from({ length: SKELETONS }, (_, index) => (
              <li key={index} data-skeleton aria-hidden="true" className="shrink-0">
                <span className="block aspect-[2/3] w-[8.25rem] rounded-lg bg-raised md:w-full" />
                <span className="mt-3 block h-3.5 w-3/4 rounded bg-raised" />
                <span className="mt-1.5 block h-3 w-1/2 rounded bg-raised" />
              </li>
            ))
          : items.map((item) => (
              <li key={`${item.tipo}-${item.id}`} className="shrink-0 snap-start">
                <MediaCard title={item} showType={showType} from={from} />
              </li>
            ))}
      </ul>
    </section>
  );
}
