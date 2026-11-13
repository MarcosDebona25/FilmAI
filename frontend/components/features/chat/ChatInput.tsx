"use client";

import { ArrowUp, Square } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useLayoutEffect, type RefObject } from "react";

import { useChat } from "@/components/ChatProvider";
import { MAX_MENSAJE } from "@/lib/chat";

/** Desde cuántos caracteres se muestra el contador (cerca del tope, spec `chat-ui`). */
const AVISO_CONTADOR = 400;
/** Alto máximo del campo antes de que aparezca el scroll (canvas: 140 px). */
const ALTO_MAXIMO = 140;

/**
 * Campo del chat. Enter envía y Mayús+Enter hace un salto de línea. Mientras
 * llega una respuesta se puede seguir escribiendo (queda como borrador), pero
 * el botón es «Cancelar» y Enter no envía.
 */
export function ChatInput({ campoRef }: { campoRef: RefObject<HTMLTextAreaElement | null> }) {
  const t = useTranslations("chat.input");
  const tc = useTranslations("common.actions");
  const tp = useTranslations("chat.panel");
  const { borrador, setBorrador, enviar, cancelar, enCurso } = useChat();
  const contadorId = useId();
  const vacio = !borrador.trim();
  const respondiendo = enCurso !== null;

  // El campo crece con el texto hasta 140 px. Se mide después de cada cambio:
  // primero se achica a `auto` para que `scrollHeight` sea el alto real.
  useLayoutEffect(() => {
    const campo = campoRef.current;
    if (!campo) return;
    campo.style.height = "auto";
    campo.style.height = `${Math.min(campo.scrollHeight, ALTO_MAXIMO)}px`;
  }, [borrador, campoRef]);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        enviar();
      }}
      className="flex flex-col gap-2 px-4 pt-3.5 pb-[max(1.25rem,env(safe-area-inset-bottom))] shadow-[inset_0_1px_0_var(--line)] md:pb-4"
    >
      <div className="flex items-end gap-2.5">
        <label htmlFor={`${contadorId}-campo`} className="sr-only">
          {t("label")}
        </label>
        <textarea
          ref={campoRef}
          id={`${contadorId}-campo`}
          rows={1}
          value={borrador}
          maxLength={MAX_MENSAJE}
          placeholder={t("placeholder")}
          aria-describedby={borrador.length >= AVISO_CONTADOR ? contadorId : undefined}
          onChange={(event) => setBorrador(event.target.value)}
          onKeyDown={(event) => {
            // `isComposing`: con un teclado que arma caracteres (japonés,
            // acentos en algunos sistemas) Enter confirma la letra, no envía.
            if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
            event.preventDefault();
            if (!respondiendo) enviar();
          }}
          className="min-h-12 flex-1 resize-none rounded-[0.875rem] bg-background px-4 py-[0.8125rem] text-base leading-[1.4] text-foreground shadow-[inset_0_0_0_1px_var(--line)] placeholder:text-fg-3 focus-visible:outline-2 focus-visible:outline-ring"
        />
        {/* Un `key` por botón: si React reusara el mismo nodo, al cancelar el
            botón pasaría a `submit` antes de que el navegador aplique la acción
            por defecto del clic, y la pregunta se volvería a enviar. */}
        {respondiendo ? (
          <button
            key="cancelar"
            type="button"
            onClick={(event) => {
              event.preventDefault();
              cancelar();
              // El botón se desmonta al cancelar: sin esto el foco cae al `body`,
              // fuera del campo, dentro de un diálogo modal.
              campoRef.current?.focus({ preventScroll: true });
            }}
            aria-label={tc("cancel")}
            className="grid size-12 flex-none place-items-center rounded-[0.875rem] bg-raised-2 text-foreground shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            <Square aria-hidden="true" className="size-4 fill-current" />
          </button>
        ) : (
          <button
            key="enviar"
            type="submit"
            aria-label={t("send")}
            aria-disabled={vacio}
            onClick={(event) => {
              if (vacio) event.preventDefault();
            }}
            className="grid size-12 flex-none place-items-center rounded-[0.875rem] bg-primary text-on-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring aria-disabled:cursor-not-allowed aria-disabled:opacity-40"
          >
            <ArrowUp aria-hidden="true" className="size-5" strokeWidth={2.2} />
          </button>
        )}
      </div>
      {borrador.length >= AVISO_CONTADOR && (
        <p id={contadorId} className="m-0 text-right text-xs text-fg-3 tabular-nums">
          {t("counter", { count: borrador.length, max: MAX_MENSAJE })}
        </p>
      )}
      <p className="m-0 hidden text-xs text-fg-3 md:block">{tp("disclaimer")}</p>
    </form>
  );
}
