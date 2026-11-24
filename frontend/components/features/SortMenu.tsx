"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ArrowDownUp, Check, ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";

import { ETIQUETA_ORDEN, ORDENES, type Orden } from "@/lib/search";
import { cn } from "@/lib/utils";

/**
 * Orden de Buscar en escritorio (canvas «Explore · sort», opción C1): un botón
 * al borde derecho de la fila que abre un menú con los seis órdenes. Desde 1280
 * px lleva rótulo y valor; por debajo, solo el ícono, con un punto si el orden
 * no es «Popular». Teclado: flechas, Inicio/Fin, Escape (devuelve el foco al
 * botón), Tab y clic afuera cierran. En celular el orden va en `FiltersSheet`.
 */
export function SortMenu({ valor, onChange }: { valor: Orden; onChange: (orden: Orden) => void }) {
  const t = useTranslations();
  const [abierto, setAbierto] = useState(false);
  const boton = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const tituloId = useId();
  const etiquetaDe = (orden: Orden) => t(`common.sort.${ETIQUETA_ORDEN[orden]}`);

  function cerrar(devolverFoco = true) {
    setAbierto(false);
    if (devolverFoco) boton.current?.focus({ preventScroll: true });
  }

  function elegir(orden: Orden) {
    onChange(orden);
    cerrar();
  }

  useEffect(() => {
    if (!abierto) return;
    menu.current?.querySelector<HTMLElement>('[aria-checked="true"]')?.focus();
  }, [abierto]);

  function alTeclear(evento: React.KeyboardEvent) {
    if (evento.key === "Escape") {
      // No debe llegar al atajo de la página, que sale de Buscar.
      evento.stopPropagation();
      cerrar();
      return;
    }
    if (evento.key === "Tab") {
      cerrar(false);
      return;
    }
    const pasos: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 };
    if (evento.key === "Home" || evento.key === "End" || evento.key in pasos) {
      evento.preventDefault();
      const items = Array.from(
        menu.current?.querySelectorAll<HTMLElement>("[role=menuitemradio]") ?? []
      );
      const actual = items.indexOf(document.activeElement as HTMLElement);
      const siguiente =
        evento.key === "Home"
          ? 0
          : evento.key === "End"
            ? items.length - 1
            : (actual + pasos[evento.key] + items.length) % items.length;
      items[siguiente]?.focus();
    }
  }

  return (
    <div className="relative ml-auto">
      <button
        ref={boton}
        type="button"
        aria-haspopup="menu"
        aria-expanded={abierto}
        aria-label={t("reviews.filters.orderPrefix", { sortLabel: etiquetaDe(valor) })}
        onClick={() => setAbierto((antes) => !antes)}
        className="relative inline-flex size-12 cursor-pointer items-center justify-center gap-2 rounded-[0.625rem] text-sm font-semibold whitespace-nowrap shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring min-[85.375rem]:w-auto min-[85.375rem]:pr-3 min-[85.375rem]:pl-3.5 min-[85.375rem]:text-[0.9375rem]"
      >
        <ArrowDownUp
          aria-hidden="true"
          className="size-5 text-fg-2 min-[85.375rem]:size-[1.125rem]"
        />
        <span className="hidden font-medium text-fg-3 min-[85.375rem]:inline">
          {t("common.filters.sortLabel")}
        </span>
        <span className="hidden min-[85.375rem]:inline">{etiquetaDe(valor)}</span>
        <ChevronDown aria-hidden="true" className="hidden size-4 text-fg-3 min-[85.375rem]:block" />
        {valor !== "popular" && (
          <span
            aria-hidden="true"
            className="absolute top-[0.5625rem] right-[0.5625rem] size-2 rounded-full bg-primary min-[85.375rem]:hidden"
          />
        )}
      </button>

      {abierto && (
        <>
          <div aria-hidden="true" onClick={() => cerrar(false)} className="fixed inset-0 z-40" />
          <div
            ref={menu}
            role="menu"
            aria-labelledby={tituloId}
            onKeyDown={alTeclear}
            className="absolute top-full right-0 z-50 mt-2 flex w-[15.5rem] flex-col rounded-[0.875rem] bg-raised p-1.5 shadow-[0_18px_46px_rgb(0_0_0/0.5),inset_0_0_0_1px_var(--line)]"
          >
            <span
              id={tituloId}
              className="px-2.5 pt-2 pb-1 text-[0.6875rem] font-semibold tracking-[0.08em] text-fg-3 uppercase"
            >
              {t("common.filters.sortByLabel")}
            </span>
            {ORDENES.map((orden) => {
              const activo = orden === valor;
              return (
                <button
                  key={orden}
                  type="button"
                  role="menuitemradio"
                  aria-checked={activo}
                  onClick={() => elegir(orden)}
                  className={cn(
                    "flex h-11 cursor-pointer items-center justify-between rounded-[0.625rem] px-2.5 text-left text-[0.9375rem] hover:bg-raised-2 focus-visible:outline-2 focus-visible:outline-ring",
                    activo ? "bg-raised-2 font-semibold" : "font-medium"
                  )}
                >
                  {etiquetaDe(orden)}
                  {activo && <Check aria-hidden="true" className="size-[1.125rem] text-primary" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
