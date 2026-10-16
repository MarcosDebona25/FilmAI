"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { Check, Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { ApiError, extraerErroresPorCampo } from "@/lib/api";
import type { ListaFicha } from "@/lib/title-lists";
import { mensajeDeError } from "@/components/features/title/RatingDialog";

/**
 * Menú «Add to list» (canvas): las listas propias con su casilla, y crear una
 * nueva en el lugar. En escritorio es un panel bajo el botón; en celular, una
 * hoja desde abajo con fondo oscuro. Escape y el clic afuera lo cierran.
 */
export function ListsMenu({
  titulo,
  listas,
  pendiente,
  onAlternar,
  onCrear,
  onClose,
}: {
  titulo: string;
  listas: ListaFicha[];
  pendiente: number | null;
  onAlternar: (lista: ListaFicha) => void;
  onCrear: (nombre: string) => Promise<void>;
  onClose: () => void;
}) {
  const t = useTranslations();
  const ref = useRef<HTMLDivElement>(null);
  const [creando, setCreando] = useState(false);
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const tituloId = useId();
  const campoId = useId();

  useEffect(() => {
    ref.current?.querySelector<HTMLElement>("button, input")?.focus();
  }, []);

  async function crear(event: FormEvent) {
    event.preventDefault();
    const limpio = nombre.trim();
    if (!limpio) {
      setError(t("title.lists.nameRequiredError"));
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await onCrear(limpio);
      setCreando(false);
      setNombre("");
    } catch (motivo) {
      setError(
        motivo instanceof ApiError && motivo.code === "list_name_duplicated"
          ? t("title.lists.nameDuplicateError")
          : motivo instanceof ApiError
            ? (extraerErroresPorCampo(motivo).nombre ?? motivo.message)
            : mensajeDeError(motivo)
      );
    } finally {
      setEnviando(false);
    }
  }

  const fila =
    "flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-[10px] px-3 text-left text-[15px] hover:bg-raised-2 focus-visible:outline-2 focus-visible:outline-ring";

  return (
    <>
      <div
        aria-hidden="true"
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/55 md:bg-transparent"
      />
      <div
        ref={ref}
        role="dialog"
        aria-label={t("title.lists.addTitleLabel", { title: titulo })}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.stopPropagation();
            onClose();
          }
        }}
        className="fixed inset-x-0 bottom-0 z-50 flex max-h-[80dvh] flex-col gap-0.5 overflow-y-auto rounded-t-[20px] bg-raised px-3 pt-2.5 pb-6 shadow-[0_-10px_40px_rgb(0_0_0/0.4)] md:absolute md:inset-x-auto md:top-14 md:bottom-auto md:left-0 md:w-[340px] md:rounded-[14px] md:p-2 md:shadow-[0_18px_46px_rgb(0_0_0/0.45),inset_0_0_0_1px_var(--line)]"
      >
        <span aria-hidden="true" className="mx-auto mb-2 h-1 w-10 rounded-full bg-line md:hidden" />
        <div className="flex items-center justify-between px-2 pb-2 md:hidden">
          <h2 id={tituloId} className="font-display text-[30px] leading-none">
            {t("common.lists.add")}
          </h2>
          <button
            type="button"
            aria-label={t("common.actions.close")}
            onClick={onClose}
            className="-mr-1.5 grid size-11 cursor-pointer place-items-center text-fg-2"
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </div>
        <p className="mx-3 my-1.5 text-[13px] font-semibold text-fg-3">
          {t("title.lists.heading")}
        </p>
        {listas.map((lista) => (
          <button
            key={lista.id}
            type="button"
            aria-pressed={lista.contiene}
            disabled={pendiente === lista.id}
            onClick={() => onAlternar(lista)}
            className={`${fila} font-medium`}
          >
            <span
              aria-hidden="true"
              className={`grid size-[22px] shrink-0 place-items-center rounded-md ${lista.contiene ? "bg-primary text-on-accent" : "shadow-[inset_0_0_0_1.5px_var(--fg-3)]"}`}
            >
              {lista.contiene && <Check className="size-3.5" strokeWidth={3} />}
            </span>
            <span className="min-w-0 flex-1 truncate">{lista.nombre}</span>
            <span className="text-[13px] text-fg-3 tabular-nums">{lista.cantidad_items}</span>
          </button>
        ))}
        <span aria-hidden="true" className="mx-1 my-1.5 h-px bg-line" />
        {creando ? (
          <form onSubmit={crear} className="flex flex-col gap-2 px-3 py-1.5">
            <label htmlFor={campoId} className="text-sm font-semibold">
              {t("title.lists.newNameLabel")}
            </label>
            <input
              id={campoId}
              type="text"
              maxLength={80}
              value={nombre}
              onChange={(event) => setNombre(event.target.value)}
              placeholder={t("title.lists.nameExamplePlaceholder")}
              aria-invalid={error ? true : undefined}
              disabled={enviando}
              className="h-11 rounded-lg bg-background px-3 shadow-[inset_0_0_0_1px_var(--line)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-ring"
            />
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setCreando(false);
                  setError(null);
                }}
                className="h-11 cursor-pointer rounded-lg px-3 text-fg-2 hover:text-foreground md:h-10"
              >
                {t("common.actions.cancel")}
              </button>
              <button
                type="submit"
                disabled={enviando}
                className="h-11 cursor-pointer rounded-lg bg-primary px-4 font-semibold text-primary-foreground disabled:opacity-60 md:h-10"
              >
                {t("title.lists.createAndAdd")}
              </button>
            </div>
          </form>
        ) : (
          <button
            type="button"
            onClick={() => setCreando(true)}
            className={`${fila} font-semibold`}
          >
            <Plus aria-hidden="true" className="size-5 shrink-0 text-primary" />
            {t("title.lists.newAction")}
          </button>
        )}
        <p className="mx-3 mt-1.5 mb-1 text-[13px] text-fg-3">{t("title.lists.defaultsHint")}</p>
        <button
          type="button"
          onClick={onClose}
          className="mt-2 h-12 cursor-pointer rounded-lg bg-raised-2 font-semibold md:hidden"
        >
          {t("common.actions.done")}
        </button>
      </div>
    </>
  );
}
