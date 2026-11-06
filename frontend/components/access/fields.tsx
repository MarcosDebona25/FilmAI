"use client";

import { Check, CircleAlert, Eye, EyeOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useState, type ComponentProps, type ReactNode } from "react";

import { cn } from "@/lib/utils";

export const fieldClass =
  "h-[3.25rem] w-full rounded-[0.625rem] border-0 bg-card px-4 text-base text-foreground shadow-[inset_0_0_0_1px_var(--field-border)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring aria-[invalid=true]:shadow-[inset_0_0_0_1px_var(--destructive)]";

export function FieldError({ id, children }: { id?: string; children: ReactNode }) {
  if (!children) return null;
  return (
    <p
      id={id}
      role="alert"
      className="flex items-center gap-1.5 text-[0.8125rem] font-semibold text-destructive"
    >
      <CircleAlert aria-hidden="true" className="size-[0.9375rem] flex-none" />
      {children}
    </p>
  );
}

export function FieldHelp({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} className="text-[0.8125rem] text-fg-3">
      {children}
    </p>
  );
}

/**
 * Renglón de mensajes debajo de un campo (issue #175): error y ayuda ocupan la
 * misma celda de una grilla, así que al cambiar uno por otro el campo no cambia
 * de alto. La ayuda queda invisible (y fuera del árbol de accesibilidad)
 * mientras hay error. Con `reserve`, un campo sin ayuda guarda un renglón vacío
 * para que el error no empuje lo que sigue al aparecer.
 */
export function FieldMessage({
  id,
  error,
  help,
  reserve = false,
  className,
  children,
  ...region
}: {
  id?: string;
  error?: string | null;
  help?: ReactNode;
  reserve?: boolean;
  className?: string;
  /** Contenido extra fuera de la grilla (p. ej. un texto `sr-only`). */
  children?: ReactNode;
  "aria-live"?: "polite";
}) {
  if (!error && !help && !reserve && !children) return null;
  return (
    <div
      id={id}
      {...region}
      className={cn(
        "grid text-[0.8125rem] [&>*]:col-start-1 [&>*]:row-start-1",
        reserve && "min-h-[1lh]",
        className
      )}
    >
      {help ? (
        <div className={error ? "invisible" : undefined}>
          <FieldHelp>{help}</FieldHelp>
        </div>
      ) : null}
      {error ? <FieldError>{error}</FieldError> : null}
      {children}
    </div>
  );
}

type TextFieldProps = Omit<ComponentProps<"input">, "id"> & {
  label: string;
  id?: string;
  help?: ReactNode;
  error?: string | null;
  /**
   * Validación positiva (p. ej. «Disponible»): se ve como un ✓ dentro del
   * campo y el texto lo anuncia la región viva. Pasar `null` (no `undefined`)
   * desde el inicio para que la región exista antes del primer aviso.
   */
  ok?: string | null;
  /** Guarda un renglón para el error aunque el campo no tenga ayuda. */
  reserveMessage?: boolean;
  prefix?: string;
};

export function TextField({
  label,
  id,
  help,
  error,
  ok,
  reserveMessage = false,
  prefix,
  ...input
}: TextFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  const describedBy = `${fieldId}-info`;
  const conOk = ok !== undefined;
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={fieldId} className="text-sm font-semibold">
        {label}
      </label>
      <div className="relative">
        {prefix && (
          <span aria-hidden="true" className="absolute top-3.5 left-4 text-fg-3">
            {prefix}
          </span>
        )}
        <input
          id={fieldId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(fieldClass, prefix && "pl-9", conOk && "pr-11")}
          {...input}
        />
        {conOk && ok && !error ? (
          <Check
            aria-hidden="true"
            strokeWidth={2.5}
            className="pointer-events-none absolute top-1/2 right-4 size-5 -translate-y-1/2 text-ok"
          />
        ) : null}
      </div>
      {/* Con `ok`, el contenedor es la región viva: existe desde el inicio y el
          aviso se agrega después (un `aria-live` que nace con texto no se anuncia). */}
      <FieldMessage
        id={describedBy}
        aria-live={conOk ? "polite" : undefined}
        error={error}
        help={help}
        reserve={reserveMessage || conOk}
      >
        {ok && !error ? <span className="sr-only">{ok}</span> : null}
      </FieldMessage>
    </div>
  );
}

type PasswordFieldProps = Omit<ComponentProps<"input">, "id" | "type"> & {
  label: string;
  id?: string;
  error?: string | null;
  children?: ReactNode;
  /** Acción debajo del campo, a la derecha (p. ej. «¿Olvidaste tu contraseña?»). */
  labelAction?: ReactNode;
  /** Guarda un renglón para el error, debajo de `children`, aunque no haya error. */
  reserveMessage?: boolean;
};

export function PasswordField({
  label,
  id,
  error,
  children,
  labelAction,
  reserveMessage = false,
  ...input
}: PasswordFieldProps) {
  const t = useTranslations("common.password");
  const generated = useId();
  const fieldId = id ?? generated;
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative flex flex-col gap-2">
      <label htmlFor={fieldId} className="text-sm font-semibold">
        {label}
      </label>
      <div className="relative">
        <input
          id={fieldId}
          type={visible ? "text" : "password"}
          aria-invalid={error ? true : undefined}
          aria-describedby={`${fieldId}-info`}
          className={`${fieldClass} pr-[3.25rem]`}
          {...input}
        />
        <button
          type="button"
          aria-label={t("showLabel")}
          aria-pressed={visible}
          onClick={() => setVisible((value) => !value)}
          className="absolute top-1 right-1 grid size-11 place-items-center rounded-lg text-fg-3 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          {visible ? (
            <EyeOff aria-hidden="true" className="size-5" />
          ) : (
            <Eye aria-hidden="true" className="size-5" />
          )}
        </button>
      </div>
      {labelAction && <div className="flex justify-end">{labelAction}</div>}
      {/* El error va después de `children` (las reglas de la contraseña): así el
          renglón reservado queda al final del campo y se lee como espacio. */}
      <div id={`${fieldId}-info`} className="flex flex-col gap-2">
        {children}
        <FieldMessage error={error} reserve={reserveMessage} />
      </div>
    </div>
  );
}
