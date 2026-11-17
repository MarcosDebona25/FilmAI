"use client";

import { useRef, type KeyboardEvent } from "react";
import { Check, Clock, CirclePlay, Eye, X, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";
import { ESTADOS, type Estado } from "@/lib/title-status";
import { useMenuDialogo } from "@/lib/use-menu-dialogo";
import { cn } from "@/lib/utils";

/** Ícono de cada estado: el mismo en el botón de la ficha y en el menú. */
export const ICONO_ESTADO: Record<Estado, LucideIcon> = {
  pendientes: Clock,
  viendo: CirclePlay,
  vistas: Eye,
};

const FILAS = '[role="menuitemradio"], [role="menuitem"]';

/**
 * Menú de estado de la ficha (canvas «Watching · title page»): Watchlist,
 * Watching y Watched como radios, y «Remove status». En escritorio es un panel
 * pegado al botón; en celular, una hoja desde abajo con filas de 60 px. Es un
 * `<dialog>` modal, como el de «Add to list»: el fondo queda inerte y Escape o
 * el clic afuera lo cierran. Con las flechas se mueve el foco entre las filas.
 */
export function StatusMenu({
  titulo,
  estado,
  onElegir,
  onClose,
}: {
  titulo: string;
  estado: Estado | null;
  /** Se llama con el estado elegido, o `null` para quitarlo. */
  onElegir: (estado: Estado | null) => void;
  onClose: () => void;
}) {
  const t = useTranslations();
  const ref = useRef<HTMLDialogElement>(null);

  // Al abrir, el foco va a la fila marcada (o a la primera si no hay estado).
  useMenuDialogo(
    ref,
    (dialogo) =>
      dialogo.querySelector<HTMLElement>('[aria-checked="true"]') ??
      dialogo.querySelector<HTMLElement>(FILAS)
  );

  function alTeclear(event: KeyboardEvent<HTMLElement>) {
    const filas = Array.from(event.currentTarget.querySelectorAll<HTMLElement>(FILAS));
    const actual = filas.indexOf(document.activeElement as HTMLElement);
    const destino =
      event.key === "ArrowDown"
        ? (actual + 1) % filas.length
        : event.key === "ArrowUp"
          ? (actual - 1 + filas.length) % filas.length
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? filas.length - 1
              : -1;
    if (destino < 0) return;
    event.preventDefault();
    filas[destino].focus();
  }

  const fila =
    "flex min-h-[3.75rem] w-full cursor-pointer items-center gap-3.5 rounded-xl px-3.5 py-1.5 text-left text-base hover:bg-raised-2 focus-visible:outline-2 focus-visible:outline-ring md:min-h-14 md:text-[0.9375rem]";

  return (
    <dialog
      ref={ref}
      aria-label={t("title.status.menuLabel", { title: titulo })}
      aria-modal="true"
      onKeyDown={(event) => mantenerFocoEnDialogo(event.nativeEvent, ref.current)}
      onCancel={(event) => {
        // Escape: se desmonta desde el padre, que también devuelve el foco.
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        // Clic en el fondo (o fuera de la hoja): el `<dialog>` es el objetivo.
        if (event.target !== ref.current) return;
        const caja = ref.current.getBoundingClientRect();
        const { clientX: x, clientY: y } = event;
        if (x < caja.left || x > caja.right || y < caja.top || y > caja.bottom) onClose();
      }}
      className="fixed inset-x-0 top-auto bottom-0 m-0 max-h-[80dvh] w-full max-w-none flex-col gap-0.5 overflow-y-auto overscroll-contain rounded-t-[1.25rem] border-0 bg-raised px-3 pt-2.5 pb-[max(1.5rem,env(safe-area-inset-bottom))] text-foreground shadow-[0_-10px_40px_rgb(0_0_0/0.4)] backdrop:bg-black/55 open:flex md:inset-x-auto md:top-[var(--menu-y)] md:bottom-auto md:left-[var(--menu-x)] md:max-h-[var(--menu-max)] md:w-[18.75rem] md:overscroll-auto md:rounded-[0.875rem] md:p-2 md:shadow-[0_18px_46px_rgb(0_0_0/0.45),inset_0_0_0_1px_var(--line)] md:backdrop:bg-transparent"
    >
      <span aria-hidden="true" className="mx-auto mb-2 h-1 w-10 rounded-full bg-line md:hidden" />
      <div className="flex items-center justify-between px-2 pb-2 md:hidden">
        <h2 className="font-display text-[1.875rem] leading-none">
          {t("title.status.menuLabel", { title: titulo })}
        </h2>
        <button
          type="button"
          aria-label={t("common.actions.close")}
          onClick={onClose}
          className="-mr-1.5 grid size-11 cursor-pointer place-items-center text-fg-2"
        >
          <X aria-hidden="true" className="size-5" />
        </button>
      </div>
      <div
        role="menu"
        aria-label={t("title.status.menuLabel", { title: titulo })}
        onKeyDown={alTeclear}
        className="flex flex-col gap-0.5"
      >
        {ESTADOS.map((candidato) => {
          const Icono = ICONO_ESTADO[candidato];
          const marcado = candidato === estado;
          return (
            <button
              key={candidato}
              type="button"
              role="menuitemradio"
              aria-checked={marcado}
              onClick={() => onElegir(candidato)}
              className={fila}
            >
              <Icono
                aria-hidden="true"
                className={cn(
                  "size-5 shrink-0",
                  candidato === "vistas" ? "text-fg-2" : "text-primary"
                )}
              />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="font-semibold">{t(`enums.defaultList.${candidato}`)}</span>
                <span className="text-[0.8125rem] text-fg-3">
                  {t(`title.status.hint.${candidato}`)}
                </span>
              </span>
              {marcado && (
                <Check aria-hidden="true" className="size-[1.125rem]" strokeWidth={2.5} />
              )}
            </button>
          );
        })}
        {estado && (
          <>
            <span aria-hidden="true" className="mx-3.5 my-1.5 h-px bg-line" />
            <button
              type="button"
              role="menuitem"
              onClick={() => onElegir(null)}
              className={cn(fila, "min-h-[3.25rem] text-fg-2 md:min-h-12")}
            >
              {t("title.status.remove")}
            </button>
          </>
        )}
      </div>
    </dialog>
  );
}
