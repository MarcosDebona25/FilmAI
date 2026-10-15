"use client";

import { useId, useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";

import type { AvatarOption } from "@/components/AccountProvider";
import { DialogShell } from "@/components/features/title/DialogShell";
import { cn } from "@/lib/utils";

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
      <h2 id={titulo} className="font-display text-[30px] leading-none md:text-[36px]">
        {t("avatar.chooseTitle")}
      </h2>
      <div
        role="radiogroup"
        aria-label={t("avatar.optionsLabel")}
        className="grid grid-cols-4 gap-3 sm:grid-cols-6"
      >
        {avatares.map((avatar, i) => {
          const marcado = avatar.id === elegido;
          return (
            <button
              key={avatar.id}
              type="button"
              role="radio"
              aria-checked={marcado}
              aria-label={t("avatar.optionLabel", { number: String(i + 1) })}
              // Foco itinerante: solo el elegido entra con Tab; las flechas cambian.
              tabIndex={marcado ? 0 : -1}
              onClick={() => setElegido(avatar.id)}
              onKeyDown={(evento) => {
                const paso = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[
                  evento.key
                ];
                if (!paso) return;
                evento.preventDefault();
                const siguiente = avatares[(i + paso + avatares.length) % avatares.length];
                setElegido(siguiente.id);
                const grupo = evento.currentTarget.parentElement;
                grupo
                  ?.querySelectorAll<HTMLElement>("[role='radio']")
                  [(i + paso + avatares.length) % avatares.length]?.focus();
              }}
              className={cn(
                "relative aspect-square cursor-pointer overflow-hidden rounded-full focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring",
                marcado && "shadow-[0_0_0_3px_var(--raised),0_0_0_5px_var(--primary)]"
              )}
            >
              <Image src={avatar.src} alt="" fill sizes="96px" className="object-cover" />
            </button>
          );
        })}
      </div>
      <div className="grid grid-cols-2 gap-2.5 md:flex md:justify-end">
        <button
          type="button"
          onClick={onClose}
          className="h-[52px] cursor-pointer rounded-[10px] px-4 font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-ring md:h-12 md:font-medium md:shadow-none"
        >
          {t("actions.cancel")}
        </button>
        <button
          type="button"
          onClick={() => onSave(elegido)}
          className="h-[52px] cursor-pointer rounded-[10px] bg-primary px-6 font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:h-12"
        >
          {t("actions.save")}
        </button>
      </div>
    </DialogShell>
  );
}
