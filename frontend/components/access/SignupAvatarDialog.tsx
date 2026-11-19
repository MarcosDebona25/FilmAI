"use client";

import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useId, useState } from "react";
import { useTranslations } from "next-intl";

import type { AvatarOption } from "@/components/AccountProvider";
import { AvatarRadioGroup } from "@/components/AvatarRadioGroup";
import { DialogShell } from "@/components/features/title/DialogShell";
import { useEscritorio } from "@/lib/use-escritorio";
import { cn } from "@/lib/utils";

// Tres filas por página: 6 por fila en escritorio y 4 en celular.
const POR_PAGINA = { escritorio: 18, celular: 12 };

/**
 * «Choose your avatar» del registro (canvas, sección 16). Elegir un avatar solo
 * lo marca: la elección vive acá adentro hasta «Use this avatar», que la aplica
 * y cierra. «Cancel», la ✕, el fondo y Escape cierran sin cambios.
 *
 * El catálogo se ve de a páginas de 3 filas. El tamaño de página sale del mismo
 * corte (`md:`) que las columnas de la grilla y que la forma del `DialogShell`.
 * Cambiar de página no toca la elección, y las flechas del teclado del
 * `radiogroup` se mueven dentro de la página visible.
 *
 * `DialogShell` (el `<dialog>` nativo) atrapa el foco y lo devuelve a «Choose».
 */
export function SignupAvatarDialog({
  avatares,
  avatarId,
  onUse,
  onClose,
}: {
  avatares: AvatarOption[];
  avatarId: number;
  onUse: (id: number) => void;
  onClose: () => void;
}) {
  const t = useTranslations("auth.signUp");
  const common = useTranslations("common.actions");
  const titulo = useId();
  const [elegido, setElegido] = useState(avatarId);
  const porPagina = useEscritorio() ? POR_PAGINA.escritorio : POR_PAGINA.celular;
  // Se guarda la posición de un avatar visible, no el número de página: si el
  // ancho cruza el corte, la página nueva sigue mostrando ese avatar. Al abrir
  // es el avatar actual.
  const [ancla, setAncla] = useState(() =>
    Math.max(
      0,
      avatares.findIndex((avatar) => avatar.id === avatarId)
    )
  );
  const paginas = Math.max(1, Math.ceil(avatares.length / porPagina));
  const pagina = Math.min(Math.floor(ancla / porPagina), paginas - 1);
  const desde = pagina * porPagina;
  const irA = (destino: number) => {
    if (destino >= 0 && destino < paginas) setAncla(destino * porPagina);
  };
  // En los extremos la flecha queda a la vista pero inerte (`aria-disabled`, no
  // `disabled`): la fila no se mueve y el foco no se pierde.
  const flecha = (
    clave: "avatarPrevious" | "avatarMore",
    destino: number,
    Icono: typeof ChevronLeft
  ) => {
    const inerte = destino < 0 || destino >= paginas;
    return (
      <button
        type="button"
        aria-label={t(clave)}
        aria-disabled={inerte}
        onClick={() => irA(destino)}
        className={cn(
          "grid size-11 flex-none place-items-center rounded-full bg-raised-2 text-foreground shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
          inerte ? "cursor-default opacity-40" : "cursor-pointer"
        )}
      >
        <Icono aria-hidden="true" className="size-5" />
      </button>
    );
  };

  return (
    <DialogShell
      labelledBy={titulo}
      onClose={onClose}
      cerrarConFondo
      // El foco arranca en el avatar marcado: es un radiogroup.
      initialFocus={(dialogo) => dialogo.querySelector<HTMLElement>("[aria-checked='true']")}
    >
      <div className="flex items-center justify-between gap-3">
        <h2 id={titulo} className="font-display text-[1.875rem] leading-none">
          {t("avatarLabel")}
        </h2>
        <button
          type="button"
          aria-label={common("close")}
          onClick={onClose}
          className="-mr-2 grid size-11 flex-none cursor-pointer place-items-center rounded-full text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          <X aria-hidden="true" className="size-[1.125rem]" />
        </button>
      </div>
      <div className="-mb-1 flex flex-col gap-4">
        {/* Las tres filas tienen alto fijo: una última página corta no achica el diálogo. */}
        <AvatarRadioGroup
          avatares={avatares.slice(desde, desde + porPagina)}
          desde={desde}
          elegido={elegido}
          onChange={setElegido}
          className="grid-cols-4 grid-rows-[repeat(3,4.5rem)] items-center justify-items-center gap-4 md:grid-cols-6 [&>button]:w-full [&>button]:max-w-[4.5rem] [&>button]:bg-raised-2"
        />
        <div className="flex items-center justify-center gap-4">
          {flecha("avatarPrevious", pagina - 1, ChevronLeft)}
          <p
            aria-live="polite"
            className="min-w-16 text-center text-sm font-semibold text-fg-2 tabular-nums"
          >
            {t("avatarPage", { page: String(pagina + 1), pages: String(paginas) })}
          </p>
          {flecha("avatarMore", pagina + 1, ChevronRight)}
        </div>
      </div>
      <div className="-mx-5 flex justify-end gap-3 px-5 pt-4 shadow-[0_-1px_0_var(--line)] md:-mx-7 md:px-7">
        <button
          type="button"
          onClick={onClose}
          className="h-[3.25rem] cursor-pointer rounded-[0.625rem] px-[1.375rem] font-semibold text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          {common("cancel")}
        </button>
        <button
          type="button"
          onClick={() => onUse(elegido)}
          className="h-[3.25rem] cursor-pointer rounded-[0.625rem] bg-primary px-[1.375rem] font-semibold text-primary-foreground hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {t("avatarUse")}
        </button>
      </div>
    </DialogShell>
  );
}
