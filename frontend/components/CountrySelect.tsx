"use client";

import { useId, useMemo, useRef, type FocusEventHandler } from "react";
import { useLocale, useTranslations } from "next-intl";

import { FieldError, fieldClass } from "@/components/access/fields";
import type { AppLocale } from "@/i18n/config";
import { paisesOrdenados } from "@/lib/format";
import { cn } from "@/lib/utils";

type Props = {
  value: string;
  onChange: (code: string) => void;
  /** Al salir del selector después de haberlo abierto; recorrerlo con Tab no cuenta. */
  onBlur?: FocusEventHandler<HTMLSelectElement>;
  /** Mensaje ya traducido; `FieldError` lo anuncia. */
  error?: string | null;
  id?: string;
  name?: string;
  autoFocus?: boolean;
  className?: string;
  selectClassName?: string;
  labelClassName?: string;
};

/**
 * Selector de país compartido por el registro, el alta con Google y el perfil.
 * Es un `<select>` nativo (en celular abre el selector del sistema). Arranca
 * vacío, sin adivinar por el navegador: el usuario tiene que elegir. Los
 * nombres salen de `Intl.DisplayNames`, ordenados en el idioma activo.
 */
export function CountrySelect({
  value,
  onChange,
  onBlur,
  error,
  id,
  name = "pais",
  autoFocus,
  className,
  selectClassName,
  labelClassName,
}: Props) {
  const t = useTranslations("common");
  const locale = useLocale() as AppLocale;
  const generated = useId();
  const usado = useRef(false);
  const fieldId = id ?? generated;
  const paises = useMemo(() => paisesOrdenados(locale), [locale]);
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <label htmlFor={fieldId} className={cn("text-sm font-semibold", labelClassName)}>
        {t("fields.country")}
      </label>
      <select
        id={fieldId}
        name={name}
        autoComplete="country"
        autoFocus={autoFocus}
        className={cn(fieldClass, selectClassName)}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onPointerDown={() => (usado.current = true)}
        onKeyDown={(event) => {
          if (event.key !== "Tab") usado.current = true;
        }}
        onBlur={(event) => {
          if (usado.current) onBlur?.(event);
        }}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${fieldId}-error` : undefined}
      >
        <option value="" disabled>
          {t("country.placeholder")}
        </option>
        {paises.map(({ code, name: nombre }) => (
          <option key={code} value={code}>
            {nombre}
          </option>
        ))}
      </select>
      {error && <FieldError id={`${fieldId}-error`}>{error}</FieldError>}
    </div>
  );
}
