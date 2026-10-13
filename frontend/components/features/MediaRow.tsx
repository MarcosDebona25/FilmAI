"use client";

import { useId, useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";

import { MediaCard } from "@/components/features/MediaCard";
import type { Title } from "@/lib/catalog";

const SKELETONS = 5;

/**
 * Fila con scroll horizontal del Home: título, descripción y tarjetas. En
 * escritorio, flechas que mueven casi un ancho; en celular, swipe con snap.
 * Vacía y sin cargar no se dibuja (doc 04 §5: la fila sin datos se oculta).
 */
export function MediaRow({
  title,
  description,
  items,
  showType,
  loading = false,
}: {
  title: string;
  description?: string;
  items: Title[];
  showType: boolean;
  loading?: boolean;
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
      left: direction * Math.round(element.clientWidth * 0.9),
      behavior: reduce ? "auto" : "smooth",
    });
  }

  const arrow =
    "grid size-11 cursor-pointer place-items-center rounded-full bg-raised text-fg-3 transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring";

  return (
    <section
      aria-labelledby={headingId}
      aria-busy={loading || undefined}
      className="flex flex-col gap-3.5 md:gap-[22px]"
    >
      <div className="flex items-end justify-between gap-3 pr-3 pl-5 md:px-0">
        <div className="flex min-w-0 flex-col gap-0.5">
          <h2 id={headingId} className="font-display text-[30px] leading-none md:text-[40px]">
            {title}
          </h2>
          {description && <p className="text-[13px] text-fg-3 md:text-sm">{description}</p>}
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
        className="flex snap-x snap-mandatory scroll-px-5 gap-3.5 overflow-x-auto overscroll-x-contain px-5 pt-1.5 pb-2.5 [scrollbar-width:none] md:snap-none md:gap-5 md:px-0 [&::-webkit-scrollbar]:hidden"
      >
        {loading
          ? Array.from({ length: SKELETONS }, (_, index) => (
              <li key={index} data-skeleton aria-hidden="true" className="shrink-0">
                <span className="block aspect-[2/3] w-[132px] animate-pulse rounded-lg bg-raised motion-reduce:animate-none md:w-[176px]" />
                <span className="mt-3 block h-3.5 w-3/4 rounded bg-raised" />
                <span className="mt-1.5 block h-3 w-1/2 rounded bg-raised" />
              </li>
            ))
          : items.map((item) => (
              <li key={`${item.tipo}-${item.id}`} className="shrink-0 snap-start">
                <MediaCard title={item} showType={showType} />
              </li>
            ))}
      </ul>
    </section>
  );
}
