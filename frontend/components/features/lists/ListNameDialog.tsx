"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { useLocale, useTranslations } from "next-intl";

import { DialogShell } from "@/components/features/title/DialogShell";
import type { AppLocale } from "@/i18n/config";
import { ApiError } from "@/lib/api";
import { translateError, type CodedError } from "@/lib/errors";
import { useFormats } from "@/lib/format";
import { MAX_NOMBRE, errorDeNombre } from "@/lib/lists";

/**
 * Crear o renombrar una lista (canvas «Create new list» y «Rename list»). La
 * validación local cubre lo evidente (vacío, caracteres); duplicado y nombres
 * reservados los dice el backend por código. Si falla, el diálogo sigue abierto.
 */
export function ListNameDialog({
  modo,
  inicial = "",
  onSubmit,
  onClose,
}: {
  modo: "crear" | "renombrar";
  inicial?: string;
  onSubmit: (nombre: string) => Promise<void>;
  onClose: () => void;
}) {
  const t = useTranslations();
  const formats = useFormats();
  const locale = useLocale() as AppLocale;
  const tituloId = useId();
  const campoId = useId();
  const ayudaId = useId();
  const errorId = useId();
  const campo = useRef<HTMLInputElement>(null);
  const [nombre, setNombre] = useState(inicial);
  // Un error local (vacío, caracteres) o el código del backend; se traduce al
  // renderizar, así sigue al idioma si cambia con el diálogo abierto.
  const [error, setError] = useState<"required" | "invalid" | CodedError | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(event: FormEvent) {
    event.preventDefault();
    if (enviando) return;
    const local = errorDeNombre(nombre);
    if (local) {
      setError(local);
      campo.current?.focus();
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await onSubmit(nombre.trim());
    } catch (motivo) {
      setError(
        motivo instanceof ApiError
          ? { code: motivo.code, params: motivo.params, errors: motivo.errors }
          : { code: "unknown" }
      );
      setEnviando(false);
      campo.current?.focus();
    }
  }

  return (
    <DialogShell
      labelledBy={tituloId}
      onClose={onClose}
      busy={enviando}
      initialFocus={() => campo.current}
      ancho="md:w-[min(520px,calc(100%-2rem))]"
    >
      <h2 id={tituloId} className="font-display text-[30px] leading-none md:text-[34px]">
        {t(modo === "crear" ? "lists.create.title" : "common.lists.renameTitle")}
      </h2>
      <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <label htmlFor={campoId} className="text-sm font-semibold">
            {t("common.lists.nameLabel")}
          </label>
          <input
            ref={campo}
            id={campoId}
            type="text"
            value={nombre}
            maxLength={MAX_NOMBRE}
            autoComplete="off"
            placeholder={t("lists.name.placeholder")}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? `${ayudaId} ${errorId}` : ayudaId}
            disabled={enviando}
            onChange={(event) => {
              setNombre(event.target.value);
              setError(null);
            }}
            className="h-12 rounded-lg bg-background px-3.5 text-base text-foreground shadow-[inset_0_0_0_1px_var(--field-border)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-ring aria-[invalid=true]:shadow-[inset_0_0_0_1px_var(--destructive)]"
          />
          <div className="flex justify-between gap-3 text-[13px] text-fg-3">
            <span id={ayudaId}>{t("lists.name.allowedCharactersHelp")}</span>
            <span aria-hidden="true" className="tabular-nums">
              {t("lists.name.counter", {
                count: formats.number(nombre.length),
                max: formats.number(MAX_NOMBRE),
              })}
            </span>
          </div>
          {error && (
            <p id={errorId} role="alert" className="text-sm text-destructive">
              {error === "required"
                ? t("lists.name.requiredError")
                : error === "invalid"
                  ? t("lists.name.invalidCharactersError")
                  : translateError(
                      error.errors?.find((entry) => entry.field === "nombre") ?? error,
                      locale
                    )}
            </p>
          )}
        </div>
        <div className="grid grid-cols-2 gap-2.5 md:flex md:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={enviando}
            className="h-[52px] cursor-pointer rounded-lg px-4 font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring md:h-12 md:font-medium md:shadow-none"
          >
            {t("common.actions.cancel")}
          </button>
          <button
            type="submit"
            disabled={enviando}
            className="h-[52px] cursor-pointer rounded-lg bg-primary px-[22px] font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-wait disabled:opacity-60 md:h-12"
          >
            {t(modo === "crear" ? "common.actions.create" : "common.actions.save")}
          </button>
        </div>
      </form>
    </DialogShell>
  );
}
