"use client";

import { X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useRef } from "react";

import { TicketMark } from "@/components/access/Logo";
import type { AppLocale } from "@/i18n/config";
import { useChat } from "@/components/ChatProvider";
import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";
import { translateError } from "@/lib/errors";

import { BurbujaUsuario, RespuestaAsistente } from "./ChatBubble";
import { ChatInput } from "./ChatInput";
import { ChatMarkdown } from "./ChatMarkdown";

/**
 * El panel del chat (canvas, sección 10): drawer de 440 px a la derecha en
 * escritorio y hoja desde abajo en celular. Es un `<dialog>` modal: con
 * `showModal()` el resto de la página queda inerte (ni foco ni clics), Escape
 * dispara `cancel` y `mantenerFocoEnDialogo` hace que Tab dé la vuelta
 * adentro. En escritorio el fondo no se oscurece, como en el canvas.
 */
export function ChatPanel() {
  const t = useTranslations("chat");
  const locale = useLocale() as AppLocale;
  const { abierto, cerrar, mensajes, enCurso, aviso, anuncio, fabRef } = useChat();
  const dialogoRef = useRef<HTMLDialogElement>(null);
  const campoRef = useRef<HTMLTextAreaElement>(null);
  const conversacionRef = useRef<HTMLDivElement>(null);
  const tituloId = useId();

  useEffect(() => {
    const dialogo = dialogoRef.current;
    if (!dialogo) return;
    if (abierto && !dialogo.open) {
      dialogo.showModal();
      campoRef.current?.focus({ preventScroll: true });
      const overflowAnterior = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = overflowAnterior;
      };
    }
    if (!abierto && dialogo.open) {
      dialogo.close();
      fabRef.current?.focus({ preventScroll: true });
    }
  }, [abierto, fabRef]);

  // Cada novedad deja a la vista lo último de la conversación.
  useEffect(() => {
    const conversacion = conversacionRef.current;
    if (conversacion) conversacion.scrollTop = conversacion.scrollHeight;
  }, [mensajes, enCurso, aviso]);

  return (
    <dialog
      ref={dialogoRef}
      aria-labelledby={tituloId}
      aria-modal="true"
      onKeyDown={(event) => mantenerFocoEnDialogo(event.nativeEvent, dialogoRef.current)}
      onCancel={(event) => {
        event.preventDefault();
        cerrar();
      }}
      onClick={(event) => {
        // Un clic en el fondo (fuera de la hoja) llega con el `<dialog>` como destino.
        if (event.target === dialogoRef.current) cerrar();
      }}
      className="fixed inset-x-0 top-6 bottom-0 m-0 h-auto max-h-none w-full max-w-none flex-col overflow-hidden rounded-t-[1.25rem] bg-raised p-0 text-foreground backdrop:bg-black/60 open:flex md:inset-y-0 md:right-0 md:left-auto md:h-dvh md:w-[27.5rem] md:max-w-full md:rounded-none md:shadow-[-24px_0_60px_rgb(0_0_0/0.45)] md:backdrop:bg-transparent"
    >
      <span
        aria-hidden="true"
        className="mt-2 h-1 w-10 flex-none self-center rounded-full bg-line md:hidden"
      />
      <div className="flex flex-none items-center gap-2.5 py-2.5 pr-2.5 pl-[1.125rem] shadow-[inset_0_-1px_0_var(--line)] md:gap-3 md:py-[1.125rem] md:pr-4 md:pl-[1.375rem]">
        <span
          aria-hidden="true"
          className="hidden size-10 flex-none place-items-center rounded-full bg-raised-2 md:grid"
        >
          <TicketMark width={24} height={18} />
        </span>
        <div className="flex min-w-0 flex-1 flex-col">
          <h2
            id={tituloId}
            className="m-0 font-display text-[1.625rem] leading-none md:text-[1.75rem]"
          >
            {t("panel.title")}
          </h2>
          <span className="hidden text-[0.8125rem] text-fg-3 md:block">{t("panel.subtitle")}</span>
        </div>
        <button
          type="button"
          onClick={cerrar}
          aria-label={t("panel.close")}
          className="grid size-11 flex-none place-items-center rounded-[0.625rem] text-fg-2 focus-visible:outline-2 focus-visible:outline-ring"
        >
          <X aria-hidden="true" className="size-5" />
        </button>
      </div>

      <div
        ref={conversacionRef}
        role="log"
        aria-label={t("panel.conversation")}
        className="flex flex-1 flex-col gap-[1.125rem] overflow-y-auto overscroll-contain p-[1.125rem] md:gap-[1.375rem] md:p-[1.375rem]"
      >
        {mensajes.map((mensaje) =>
          mensaje.rol === "usuario" ? (
            <BurbujaUsuario key={mensaje.id} texto={mensaje.texto} />
          ) : (
            <RespuestaAsistente
              key={mensaje.id}
              texto={mensaje.texto}
              tarjetas={mensaje.tarjetas}
            />
          )
        )}
        {enCurso && (
          <>
            <BurbujaUsuario texto={enCurso.pregunta} />
            {enCurso.respuesta ? (
              <div className="max-w-full md:max-w-[96%]">
                <ChatMarkdown texto={enCurso.respuesta} />
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className="inline-flex gap-[0.3125rem] rounded-2xl bg-raised-2 px-3.5 py-3"
                >
                  {[0, 1, 2].map((punto) => (
                    <span
                      key={punto}
                      className="size-2 animate-bounce rounded-full bg-fg-3 motion-reduce:animate-none"
                      style={{ animationDelay: `${punto * 150}ms` }}
                    />
                  ))}
                </span>
                {enCurso.estado === "searching" && (
                  <span role="status" className="text-sm text-fg-3">
                    {t("status.searching")}
                  </span>
                )}
              </div>
            )}
          </>
        )}
        {aviso && (
          <p
            role={aviso.tipo === "error" ? "alert" : "status"}
            className={`m-0 text-sm ${aviso.tipo === "error" ? "text-destructive" : "text-fg-3"}`}
          >
            {aviso.tipo === "cancelado"
              ? t("status.cancelled")
              : translateError({ code: aviso.code, params: aviso.params }, locale)}
          </p>
        )}
      </div>

      {/* Una respuesta se anuncia una vez, completa, y no delta por delta. */}
      <p aria-live="polite" className="sr-only">
        {anuncio}
      </p>

      <ChatInput campoRef={campoRef} />
    </dialog>
  );
}
