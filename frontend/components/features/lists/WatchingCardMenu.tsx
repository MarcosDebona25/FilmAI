"use client";

import { useRef } from "react";
import { Check, Ellipsis, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { CLASE_DIALOGO_MENU, FILAS, alTeclearMenu } from "@/components/features/title/StatusMenu";
import { StarIcon } from "@/components/ui/StarIcon";
import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";
import { useMenuDialogo } from "@/lib/use-menu-dialogo";
import { cn } from "@/lib/utils";

export type AccionViendo = "terminar" | "calificar" | "quitar";

/**
 * El «⋯» de una tarjeta de la lista Watching (canvas «Watching · list page»):
 * arriba a la derecha del póster, siempre visible, 36 px (44 px de área en
 * celular). Abre un menú con «Mark as finished», «Rate it…» y «Remove from
 * Watching»: un panel pegado al botón en escritorio y una hoja con «Cancel» en
 * celular. Es un `<dialog>` modal, como el menú de estado de la ficha: el fondo
 * queda inerte, Escape o el clic afuera lo cierran y el foco vuelve al «⋯».
 * Que haya un solo menú abierto lo decide quien lo usa (`abierto`).
 */
export function WatchingCardMenu({
  titulo,
  abierto,
  onAbrir,
  onCerrar,
  onElegir,
}: {
  titulo: string;
  abierto: boolean;
  onAbrir: () => void;
  onCerrar: () => void;
  onElegir: (accion: AccionViendo) => void;
}) {
  const t = useTranslations();
  const etiqueta = t("lists.watching.moreLabel", { title: titulo });
  return (
    // La caja de 44 px es el área táctil; el círculo visible mide 36 px.
    <div className="absolute top-1 right-1 size-11 md:top-2 md:right-2 md:size-9">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={abierto}
        aria-label={etiqueta}
        onClick={abierto ? onCerrar : onAbrir}
        className="group/mas grid size-full cursor-pointer place-items-center rounded-full focus-visible:outline-2 focus-visible:outline-ring"
      >
        <span className="grid size-9 place-items-center rounded-full bg-[rgb(var(--scrim)/0.78)] text-foreground opacity-90 shadow-[inset_0_0_0_1px_rgb(255_255_255/0.12)] transition-opacity group-hover/mas:opacity-100 motion-reduce:transition-none">
          <Ellipsis aria-hidden="true" className="size-[1.125rem]" />
        </span>
      </button>
      {abierto && (
        <Hoja titulo={titulo} etiqueta={etiqueta} onCerrar={onCerrar} onElegir={onElegir} />
      )}
    </div>
  );
}

function Hoja({
  titulo,
  etiqueta,
  onCerrar,
  onElegir,
}: {
  titulo: string;
  etiqueta: string;
  onCerrar: () => void;
  onElegir: (accion: AccionViendo) => void;
}) {
  const t = useTranslations();
  const ref = useRef<HTMLDialogElement>(null);
  useMenuDialogo(ref, (dialogo) => dialogo.querySelector<HTMLElement>(FILAS));

  const fila =
    "flex min-h-[3.25rem] w-full cursor-pointer items-center gap-3 rounded-[0.625rem] px-3.5 text-left text-base font-medium hover:bg-raised-2 focus-visible:outline-2 focus-visible:outline-ring md:min-h-11 md:text-[0.9375rem]";

  return (
    <dialog
      ref={ref}
      aria-label={etiqueta}
      aria-modal="true"
      onKeyDown={(event) => mantenerFocoEnDialogo(event.nativeEvent, ref.current)}
      onCancel={(event) => {
        // Escape: se desmonta desde el padre, que además devuelve el foco.
        event.preventDefault();
        onCerrar();
      }}
      onClick={(event) => {
        // Clic en el fondo (o fuera de la hoja): el `<dialog>` es el objetivo.
        if (event.target !== ref.current) return;
        const caja = ref.current.getBoundingClientRect();
        const { clientX: x, clientY: y } = event;
        if (x < caja.left || x > caja.right || y < caja.top || y > caja.bottom) onCerrar();
      }}
      className={cn(CLASE_DIALOGO_MENU, "md:w-[14.5rem]")}
    >
      <span aria-hidden="true" className="mx-auto mb-2.5 h-1 w-10 rounded-full bg-line md:hidden" />
      <p className="mb-1.5 truncate px-3.5 font-bold md:hidden">{titulo}</p>
      <div
        role="menu"
        aria-label={etiqueta}
        onKeyDown={alTeclearMenu}
        className="flex flex-col gap-0.5"
      >
        <button type="button" role="menuitem" onClick={() => onElegir("terminar")} className={fila}>
          <Check aria-hidden="true" strokeWidth={2.5} className="size-[1.125rem] text-ok" />
          {t("lists.watching.markFinished")}
        </button>
        <button
          type="button"
          role="menuitem"
          onClick={() => onElegir("calificar")}
          className={fila}
        >
          <StarIcon className="size-[1.125rem] fill-primary" />
          {t("lists.watching.rateIt")}
        </button>
        <span aria-hidden="true" className="mx-2 my-1 h-px bg-line" />
        <button
          type="button"
          role="menuitem"
          onClick={() => onElegir("quitar")}
          className={cn(fila, "text-fg-2")}
        >
          <Trash2 aria-hidden="true" className="size-[1.125rem]" />
          {t("lists.watching.remove")}
        </button>
      </div>
      <button
        type="button"
        onClick={onCerrar}
        className="mt-1.5 h-[3.25rem] cursor-pointer rounded-[0.625rem] bg-raised-2 font-semibold focus-visible:outline-2 focus-visible:outline-ring md:hidden"
      >
        {t("common.actions.cancel")}
      </button>
    </dialog>
  );
}
