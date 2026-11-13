"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";

import { MediaCard } from "@/components/features/MediaCard";
import type { Title } from "@/lib/catalog";
import { desplazamientoDePagina, gapDeColumnas } from "@/lib/paginado";
import { cn } from "@/lib/utils";

/** Tantos como la página más ancha (7 columnas desde 1440 px). */
const SKELETONS = 7;
/** Tolerancia (px) al comparar posiciones de scroll: los navegadores redondean con decimales. */
const MARGEN_SCROLL = 1;

/**
 * Altura de los pósters de una página, calculada desde el ancho de la fila:
 * póster 2:3, o sea `1,5 × ancho de la tarjeta`, con el ancho de tarjeta de la
 * grilla (`(100 % − (cols − 1) · gap) / cols`, el mismo cálculo de más abajo).
 * Las bandas de las flechas miden esto y no el alto de la fila, que suma el
 * nombre de cada tarjeta. `cqw` (unidad de container query) es el 1 % del ancho
 * del contenedor `@container` que envuelve la lista: un porcentaje no sirve
 * porque `height: %` mira el alto del padre, no su ancho.
 */
const ALTO_DE_POSTERS = "md:h-[calc(1.5_*_(100cqw_-_(var(--cols)_-_1)_*_1.25rem)_/_var(--cols))]";

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
  seeAll,
}: {
  title: string;
  description?: string;
  items: Title[];
  showType: boolean;
  loading?: boolean;
  from?: string;
  /** Enlace del encabezado al listado completo (p. ej. la lista Pendientes). */
  seeAll?: { href: string; label: string };
}) {
  const t = useTranslations("home.carousel");
  const headingId = useId();
  const list = useRef<HTMLUListElement>(null);
  // ¿Queda fila por ver a cada lado? Se calcula con el scroll de la lista y
  // decide qué flecha se dibuja (nunca la izquierda al principio ni la derecha
  // al final).
  const [hayAnteriores, setHayAnteriores] = useState(false);
  const [haySiguientes, setHaySiguientes] = useState(false);

  const actualizarFlechas = useCallback(() => {
    const element = list.current;
    if (!element) return;
    setHayAnteriores(element.scrollLeft > MARGEN_SCROLL);
    setHaySiguientes(
      element.scrollLeft + element.clientWidth < element.scrollWidth - MARGEN_SCROLL
    );
  }, []);

  // Se recalcula al cambiar lo que hay en la fila (carga, otro selector de tipo)
  // y cuando cambia el tamaño de la lista (ventana, tamaño de letra). El scroll
  // se escucha con `onScroll` en el `ul`. `ResizeObserver` es el equivalente de
  // un listener, pero para tamaños; jsdom (los tests) no lo trae.
  useEffect(() => {
    actualizarFlechas();
    const element = list.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(actualizarFlechas);
    observer.observe(element);
    return () => observer.disconnect();
  }, [actualizarFlechas, items.length, loading]);

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

  // Banda a cada costado, a la altura de los pósters y con degradé desde el
  // fondo. Transparente hasta que el mouse entra a la fila (`group/fila`) o el
  // teclado enfoca un botón o una tarjeta (`has-[a:focus-visible]`). Desde md:
  // en celular se desliza con el dedo.
  const banda = cn(
    "absolute top-1.5 z-10 hidden w-14 cursor-pointer items-center text-foreground opacity-0 transition-opacity duration-200 md:flex",
    "group-hover/fila:opacity-100 group-has-[a:focus-visible]/fila:opacity-100 focus-visible:opacity-100",
    "focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring motion-reduce:transition-none",
    ALTO_DE_POSTERS
  );

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
        {seeAll && (
          <Link
            href={seeAll.href}
            className="shrink-0 text-sm font-medium text-fg-2 no-underline hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
          >
            {seeAll.label}
          </Link>
        )}
      </div>
      <div className="group/fila @container relative">
        <ul
          ref={list}
          onScroll={actualizarFlechas}
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
        {hayAnteriores && (
          <button
            type="button"
            aria-label={t("previousRowLabel", { rowTitle: title })}
            onClick={() => move(-1)}
            className={cn(
              banda,
              "left-0 justify-start bg-linear-to-r from-background/95 to-transparent pl-2"
            )}
          >
            <ChevronLeft aria-hidden="true" className="size-8 drop-shadow" />
          </button>
        )}
        {haySiguientes && (
          <button
            type="button"
            aria-label={t("nextRowLabel", { rowTitle: title })}
            onClick={() => move(1)}
            className={cn(
              banda,
              "right-0 justify-end bg-linear-to-l from-background/95 to-transparent pr-2"
            )}
          >
            <ChevronRight aria-hidden="true" className="size-8 drop-shadow" />
          </button>
        )}
      </div>
    </section>
  );
}
