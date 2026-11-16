"use client";

import { X } from "lucide-react";
import { useId, useState } from "react";
import { useTranslations } from "next-intl";

import type { AvatarOption } from "@/components/AccountProvider";
import { AvatarRadioGroup } from "@/components/AvatarRadioGroup";
import { DialogShell } from "@/components/features/title/DialogShell";

/**
 * «Choose your avatar» del registro (canvas, sección 16). Elegir un avatar solo
 * lo marca: la elección vive acá adentro hasta «Use this avatar», que la aplica
 * y cierra. «Cancel», la ✕, el fondo y Escape cierran sin cambios.
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

  return (
    <DialogShell
      labelledBy={titulo}
      onClose={onClose}
      cierraConFondo
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
      {/* El relleno deja lugar al aro de selección dentro de la zona con scroll. */}
      <AvatarRadioGroup
        avatares={avatares}
        elegido={elegido}
        onChange={setElegido}
        className="max-h-[21.25rem] grid-cols-4 justify-items-center gap-4 overflow-y-auto p-2 sm:grid-cols-6 [&>button]:w-full [&>button]:max-w-[4.5rem] [&>button]:bg-raised-2"
      />
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
