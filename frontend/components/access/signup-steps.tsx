"use client";

import Image from "next/image";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";

import type { AvatarOption } from "@/components/AccountProvider";
import { FieldError } from "@/components/access/fields";
import { apiFetch } from "@/lib/api";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

// Piezas que comparten el registro con correo (`/register`) y el alta con
// Google (`/complete-signup`): son el mismo flujo de 3 pasos (canvas, sección 16).

export const TOTAL_PASOS = 3;

function anchoDe(paso: number) {
  return paso === TOTAL_PASOS ? "100%" : `${((paso * 100) / TOTAL_PASOS).toFixed(2)}%`;
}

/**
 * Barra de progreso de 4 px. Con `desde`, se dibuja primero en ese paso y
 * enseguida se llena hasta `paso`: el alta con Google llega en el paso 2 y la
 * barra arranca en el 33 % del paso 1 (que fue el botón de Google). Para los
 * lectores de pantalla el valor es siempre `paso`.
 */
export function SignupProgress({ paso, desde }: { paso: number; desde?: number }) {
  const t = useTranslations("auth.signUp");
  const [arrancada, setArrancada] = useState(desde === undefined);

  useEffect(() => {
    if (arrancada) return;
    // Un cuadro después del primer dibujo: sin él no habría de dónde animar.
    const id = requestAnimationFrame(() => setArrancada(true));
    return () => cancelAnimationFrame(id);
  }, [arrancada]);

  const pasoTexto = t("stepOf", { step: String(paso), total: String(TOTAL_PASOS) });

  return (
    <>
      <div
        role="progressbar"
        aria-label={t("progressLabel")}
        aria-valuemin={0}
        aria-valuemax={TOTAL_PASOS}
        aria-valuenow={paso}
        aria-valuetext={pasoTexto}
        className="relative mt-0.5 h-1 overflow-hidden rounded-full bg-raised-2"
      >
        <span
          aria-hidden="true"
          style={{ width: anchoDe(arrancada || desde === undefined ? paso : desde) }}
          className="absolute inset-y-0 left-0 rounded-full bg-primary transition-[width] duration-[400ms] ease-[cubic-bezier(.2,.7,.2,1)] motion-reduce:transition-none"
        />
      </div>
      {/* El `h1` es el mismo en los tres pasos y el `progressbar` cambia sin
          aviso: esta región viva dice «Paso N de 3» al cambiar. Existe desde el
          primer render (una región que aparece con su texto no se anuncia) y,
          al ser `sr-only`, no ocupa lugar en el layout. */}
      <p aria-live="polite" className="sr-only">
        {pasoTexto}
      </p>
    </>
  );
}

/**
 * Atributos de la celda de un paso. Todos los pasos están siempre montados en
 * la misma celda de la grilla: el que no está activo conserva su tamaño
 * (`invisible` es `visibility: hidden`) pero queda fuera del teclado y de los
 * lectores de pantalla: `inert` saca todo su contenido del foco y del árbol de
 * accesibilidad.
 */
export function celdaDePaso(cual: number, activo: number) {
  return {
    "data-paso": cual,
    inert: activo !== cual,
    "aria-hidden": activo !== cual || undefined,
    className: cn("[grid-area:1/1]", activo !== cual && "invisible"),
  };
}

/**
 * Catálogo público de avatares y el elegido. Arranca en el primero del catálogo
 * (el mismo que el backend asigna si el alta no trae `avatar_id`). Si el
 * catálogo no carga, el selector no aparece y el alta sigue sin ese campo.
 */
export function useSignupAvatars() {
  const [avatares, setAvatares] = useState<AvatarOption[]>([]);
  const [avatarId, setAvatarId] = useState<number | null>(null);

  useEffect(() => {
    let activo = true;
    apiFetch<AvatarOption[]>("/api/avatars/")
      .then((lista) => {
        if (!activo || lista.length === 0) return;
        setAvatares(lista);
        setAvatarId((actual) => actual ?? lista[0].id);
      })
      .catch(() => {});
    return () => {
      activo = false;
    };
  }, []);

  return { avatares, avatarId, setAvatarId };
}

/** Recuadro del avatar elegido con «Choose», que abre `SignupAvatarDialog`. */
export function SignupAvatarField({
  avatar,
  onChoose,
  describedBy,
}: {
  avatar: AvatarOption;
  onChoose: () => void;
  /** Id del renglón donde se muestra un error del servidor sobre el avatar. */
  describedBy?: string;
}) {
  const t = useTranslations("auth.signUp");
  return (
    <div className="flex items-center gap-4 rounded-[0.625rem] px-3.5 py-3 shadow-[inset_0_0_0_1px_var(--line)]">
      <span className="relative size-14 flex-none overflow-hidden rounded-full bg-raised-2">
        <Image src={avatar.src} alt="" fill sizes="56px" className="object-cover" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">
          {t.rich("avatarOptional", {
            hint: (chunks) => <span className="font-medium text-fg-3">{chunks}</span>,
          })}
        </p>
        <p className="text-[0.8125rem] text-fg-3">{t("avatarLaterHelp")}</p>
      </div>
      <button
        type="button"
        data-elegir-avatar
        aria-haspopup="dialog"
        aria-describedby={describedBy}
        onClick={onChoose}
        className="h-11 flex-none cursor-pointer rounded-[0.625rem] bg-secondary px-[1.125rem] font-semibold text-foreground hover:bg-line focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        {t("avatarChoose")}
      </button>
    </div>
  );
}

/**
 * Casilla de los Términos con su renglón de mensajes, que está siempre en el
 * layout: el error (o la ayuda `hint`, mientras `hintVisible`) no empuja lo que
 * sigue al aparecer ni al irse.
 */
export function SignupTerms({
  checked,
  onChange,
  error,
  hint,
  hintVisible = true,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  error?: string;
  hint?: ReactNode;
  hintVisible?: boolean;
}) {
  const t = useTranslations("auth.signUp");
  return (
    <div className="flex flex-col gap-2">
      {/* Todo el recuadro es la etiqueta: sin zonas muertas alrededor de la casilla. */}
      <label
        htmlFor="terminos"
        className={`flex cursor-pointer items-start gap-3 rounded-[0.625rem] px-3.5 py-3 ${error ? "shadow-[inset_0_0_0_1px_var(--destructive)]" : "shadow-[inset_0_0_0_1px_var(--field-border)]"}`}
      >
        <input
          id="terminos"
          name="acepta_terminos"
          required
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          aria-invalid={error ? true : undefined}
          aria-describedby="terminos-error"
          className="mt-0.5 size-5 flex-none cursor-pointer accent-primary"
        />
        <span className="flex-1 text-[0.9375rem] leading-[1.45] text-muted-foreground">
          {t.rich("termsAcceptance", {
            terms: (chunks) => (
              <Link
                href={routes.terms}
                target="_blank"
                rel="noopener"
                className="font-semibold text-foreground underline underline-offset-[3px]"
              >
                {chunks}
                <span className="sr-only"> {t("termsNewTabHint")}</span>
              </Link>
            ),
          })}
        </span>
      </label>
      {/* Error y ayuda comparten la celda: el renglón mide lo mismo con cualquiera. */}
      <div
        id="terminos-error"
        className="grid min-h-[1lh] text-[0.8125rem] [&>*]:col-start-1 [&>*]:row-start-1"
      >
        {hint ? (
          <p className={cn("text-fg-3", (error || !hintVisible) && "invisible")}>{hint}</p>
        ) : null}
        {error ? <FieldError>{error}</FieldError> : null}
      </div>
    </div>
  );
}

/** «‹ Back» de la fila de acción (44 px de alto, alineado al borde izquierdo). */
export function SignupBackButton({
  label,
  onClick,
  hidden = false,
}: {
  /** Nombre accesible: empieza con el texto visible y dice a dónde vuelve. */
  label: string;
  onClick: () => void;
  /** No se ve ni se puede usar, pero guarda su lugar. */
  hidden?: boolean;
}) {
  const t = useTranslations("auth.signUp");
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      style={{ visibility: hidden ? "hidden" : "visible" }}
      className="-ml-1 inline-flex h-11 cursor-pointer items-center gap-1.5 rounded-lg pr-2.5 pl-1 text-[0.9375rem] font-semibold text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
    >
      <ChevronLeft aria-hidden="true" className="size-[1.125rem]" />
      {t("back")}
    </button>
  );
}
