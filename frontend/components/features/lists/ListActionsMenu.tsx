"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Ellipsis } from "lucide-react";
import { useTranslations } from "next-intl";

import { DialogShell } from "@/components/features/title/DialogShell";
import { cn } from "@/lib/utils";

export interface AccionLista {
  id: string;
  etiqueta: string;
  icono?: ReactNode;
  onSelect: () => void;
  destructiva?: boolean;
  deshabilitada?: boolean;
  /** Para las que solo tienen sentido en una de las dos presentaciones. */
  solo?: "escritorio" | "celular";
}

/**
 * Botón ⋯ de una lista (canvas «Lists» y «List detail»). En escritorio abre un
 * menú anclado al botón (flechas, Escape y clic afuera); en celular, una hoja
 * desde abajo con el nombre de la lista. La presentación se decide al abrir.
 */
export function ListActionsMenu({
  etiqueta,
  titulo,
  acciones,
  className,
}: {
  /** Nombre accesible del botón («Actions for the list …»). */
  etiqueta: string;
  /** Título de la hoja de celular. */
  titulo: string;
  acciones: AccionLista[];
  className?: string;
}) {
  const t = useTranslations("common.actions");
  const [abierto, setAbierto] = useState<"escritorio" | "celular" | null>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const tituloId = useId();

  function cerrar() {
    setAbierto(null);
    boton.current?.focus({ preventScroll: true });
  }

  function elegir(accion: AccionLista) {
    setAbierto(null);
    accion.onSelect();
  }

  useEffect(() => {
    if (abierto !== "escritorio") return;
    menu.current?.querySelector<HTMLElement>('[role="menuitem"]:not(:disabled)')?.focus();
  }, [abierto]);

  const visibles = acciones.filter(
    (accion) => !accion.solo || accion.solo === (abierto ?? "escritorio")
  );

  function alTeclear(event: React.KeyboardEvent) {
    if (event.key === "Escape") {
      event.stopPropagation();
      cerrar();
      return;
    }
    if (event.key === "Tab") {
      setAbierto(null);
      return;
    }
    const pasos: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 };
    if (event.key === "Home" || event.key === "End" || event.key in pasos) {
      event.preventDefault();
      const items = Array.from(
        menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled)') ?? []
      );
      if (!items.length) return;
      const actual = items.indexOf(document.activeElement as HTMLElement);
      const siguiente =
        event.key === "Home"
          ? 0
          : event.key === "End"
            ? items.length - 1
            : (actual + pasos[event.key] + items.length) % items.length;
      items[siguiente].focus();
    }
  }

  const fila =
    "flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-[10px] px-3 text-left text-[15px] font-medium hover:bg-raised-2 focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-45";

  return (
    <div className={cn("relative", className)}>
      <button
        ref={boton}
        type="button"
        aria-haspopup="menu"
        aria-expanded={abierto !== null}
        aria-label={etiqueta}
        onClick={() =>
          setAbierto(window.matchMedia?.("(min-width: 768px)").matches ? "escritorio" : "celular")
        }
        className="grid size-11 cursor-pointer place-items-center rounded-full text-fg-2 hover:bg-raised-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
      >
        <Ellipsis aria-hidden="true" className="size-5" />
      </button>

      {abierto === "escritorio" && (
        <>
          <div aria-hidden="true" onClick={cerrar} className="fixed inset-0 z-40" />
          <div
            ref={menu}
            role="menu"
            aria-label={etiqueta}
            onKeyDown={alTeclear}
            className="absolute top-full right-0 z-50 mt-1 flex w-56 flex-col gap-0.5 rounded-[14px] bg-raised p-2 shadow-[0_18px_46px_rgb(0_0_0/0.45),inset_0_0_0_1px_var(--line)]"
          >
            {visibles.map((accion) => (
              <button
                key={accion.id}
                type="button"
                role="menuitem"
                disabled={accion.deshabilitada}
                onClick={() => elegir(accion)}
                className={cn(fila, accion.destructiva && "text-destructive")}
              >
                {accion.icono}
                {accion.etiqueta}
              </button>
            ))}
          </div>
        </>
      )}

      {abierto === "celular" && (
        <DialogShell labelledBy={tituloId} onClose={cerrar}>
          <h2 id={tituloId} className="truncate font-display text-[30px] leading-none">
            {titulo}
          </h2>
          <div className="flex flex-col gap-0.5">
            {visibles.map((accion) => (
              <button
                key={accion.id}
                type="button"
                disabled={accion.deshabilitada}
                onClick={() => elegir(accion)}
                className={cn(fila, "min-h-12", accion.destructiva && "text-destructive")}
              >
                {accion.icono}
                {accion.etiqueta}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={cerrar}
            className="h-12 cursor-pointer rounded-lg bg-raised-2 font-semibold focus-visible:outline-2 focus-visible:outline-ring"
          >
            {t("cancel")}
          </button>
        </DialogShell>
      )}
    </div>
  );
}
