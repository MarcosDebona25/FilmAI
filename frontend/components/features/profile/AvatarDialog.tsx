"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";

import type { AvatarOption } from "@/components/AccountProvider";
import { AvatarRadioGroup } from "@/components/AvatarRadioGroup";
import { DialogShell } from "@/components/features/title/DialogShell";

/**
 * «Choose an avatar» del canvas: tarjeta en escritorio, hoja en celular. La
 * elección es temporal hasta «Save», que la pasa al borrador del perfil (se
 * guarda con «Save changes»).
 */
export function AvatarDialog({
  avatares,
  avatarId,
  onSave,
  onClose,
}: {
  avatares: AvatarOption[];
  avatarId: number;
  onSave: (id: number) => void;
  onClose: () => void;
}) {
  const t = useTranslations("common");
  const titulo = useId();
  const [elegido, setElegido] = useState(avatarId);

  return (
    <DialogShell
      labelledBy={titulo}
      onClose={onClose}
      // El foco arranca en el avatar elegido: es un radiogroup.
      initialFocus={(dialogo) => dialogo.querySelector<HTMLElement>("[aria-checked='true']")}
    >
      <h2 id={titulo} className="font-display text-[1.875rem] leading-none md:text-[2.25rem]">
        {t("avatar.chooseTitle")}
      </h2>
      <AvatarRadioGroup
        avatares={avatares}
        elegido={elegido}
        onChange={setElegido}
        className="grid-cols-4 gap-3 sm:grid-cols-6"
      />
      <div className="grid grid-cols-2 gap-2.5 md:flex md:justify-end">
        <button
          type="button"
          onClick={onClose}
          className="h-[3.25rem] cursor-pointer rounded-[0.625rem] px-4 font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-ring md:h-12 md:font-medium md:shadow-none"
        >
          {t("actions.cancel")}
        </button>
        <button
          type="button"
          onClick={() => onSave(elegido)}
          className="h-[3.25rem] cursor-pointer rounded-[0.625rem] bg-primary px-6 font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:h-12"
        >
          {t("actions.save")}
        </button>
      </div>
    </DialogShell>
  );
}
