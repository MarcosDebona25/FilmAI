"use client";

import { Check, CircleAlert, Eye, EyeOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useState, type ComponentProps, type ReactNode } from "react";

export const fieldClass =
  "h-[52px] w-full rounded-[10px] border-0 bg-card px-4 text-base text-foreground shadow-[inset_0_0_0_1px_var(--line)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring aria-[invalid=true]:shadow-[inset_0_0_0_1px_var(--destructive)]";

export function FieldError({ id, children }: { id?: string; children: ReactNode }) {
  if (!children) return null;
  return (
    <p
      id={id}
      role="alert"
      className="flex items-center gap-1.5 text-[13px] font-semibold text-destructive"
    >
      <CircleAlert aria-hidden="true" className="size-[15px] flex-none" />
      {children}
    </p>
  );
}

export function FieldHelp({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} className="text-[13px] text-fg-3">
      {children}
    </p>
  );
}

export function FieldOk({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p
      id={id}
      aria-live="polite"
      className="flex items-center gap-1.5 text-[13px] font-semibold text-ok"
    >
      <Check aria-hidden="true" className="size-[15px] flex-none" strokeWidth={2.5} />
      {children}
    </p>
  );
}

type TextFieldProps = Omit<ComponentProps<"input">, "id"> & {
  label: string;
  id?: string;
  help?: ReactNode;
  error?: string | null;
  status?: ReactNode;
  prefix?: string;
};

export function TextField({ label, id, help, error, status, prefix, ...input }: TextFieldProps) {
  const generated = useId();
  const fieldId = id ?? generated;
  const describedBy = `${fieldId}-info`;
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
          className={`${fieldClass} ${prefix ? "pl-9" : ""}`}
          {...input}
        />
      </div>
      <div id={describedBy} className="flex flex-col gap-2">
        {error ? <FieldError>{error}</FieldError> : (status ?? null)}
        {!error && !status && help ? <FieldHelp>{help}</FieldHelp> : null}
        {!error && status && help ? <FieldHelp>{help}</FieldHelp> : null}
      </div>
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
};

export function PasswordField({
  label,
  id,
  error,
  children,
  labelAction,
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
          className={`${fieldClass} pr-[52px]`}
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
      <div id={`${fieldId}-info`} className="flex flex-col gap-2">
        {error ? <FieldError>{error}</FieldError> : null}
        {children}
      </div>
    </div>
  );
}
