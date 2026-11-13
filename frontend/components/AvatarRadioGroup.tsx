"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";

import type { AvatarOption } from "@/components/AccountProvider";
import { cn } from "@/lib/utils";

/**
 * Selector de avatares: un `radiogroup` con foco itinerante. Lo usan el diálogo
 * del perfil y el formulario de registro, así los dos se comportan igual.
 *
 * - Solo el avatar elegido entra con Tab (`tabIndex=0`); las flechas mueven la
 *   elección y el foco dentro del grupo.
 * - `className` decide la grilla (cada pantalla tiene su ancho). El aro de
 *   selección deja un espacio del color del fondo: por defecto el de las
 *   tarjetas (`--raised`) y, si el grupo define `--anillo`, ese.
 */
export function AvatarRadioGroup({
  avatares,
  elegido,
  onChange,
  className,
}: {
  avatares: AvatarOption[];
  elegido: number;
  onChange: (id: number) => void;
  className?: string;
}) {
  const t = useTranslations("common");

  return (
    <div role="radiogroup" aria-label={t("avatar.optionsLabel")} className={cn("grid", className)}>
      {avatares.map((avatar, i) => {
        const marcado = avatar.id === elegido;
        return (
          <button
            key={avatar.id}
            type="button"
            role="radio"
            aria-checked={marcado}
            aria-label={t("avatar.optionLabel", { number: String(i + 1) })}
            tabIndex={marcado ? 0 : -1}
            onClick={() => onChange(avatar.id)}
            onKeyDown={(evento) => {
              const paso = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[evento.key];
              if (!paso) return;
              evento.preventDefault();
              const destino = (i + paso + avatares.length) % avatares.length;
              onChange(avatares[destino].id);
              evento.currentTarget.parentElement
                ?.querySelectorAll<HTMLElement>("[role='radio']")
                [destino]?.focus();
            }}
            className={cn(
              "relative aspect-square cursor-pointer overflow-hidden rounded-full focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring",
              marcado && "shadow-[0_0_0_3px_var(--anillo,var(--raised)),0_0_0_5px_var(--primary)]"
            )}
          >
            <Image src={avatar.src} alt="" fill sizes="96px" className="object-cover" />
          </button>
        );
      })}
    </div>
  );
}
