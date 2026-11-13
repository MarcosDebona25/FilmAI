"use client";

import { MessageCircle } from "lucide-react";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { useChat } from "@/components/ChatProvider";
import { isAccessPath } from "@/lib/routes";

/**
 * El botón flotante del chat (doc 04 §3.1): en todas las pantallas salvo las
 * de acceso. Sin sesión se ve deshabilitado y no pide nada. Su nombre es el
 * texto visible («Ask FilmAI»; en celular, oculto pero leído): quien usa
 * control por voz dice lo que ve (WCAG 2.5.3, 06/11/2026).
 */
export function ChatFab() {
  const tf = useTranslations("footer.main");
  const t = useTranslations("chat.fab");
  const pathname = usePathname();
  const { habilitado, abierto, abrir, fabRef, noLeido } = useChat();
  if (isAccessPath(pathname)) return null;
  return (
    <button
      ref={fabRef}
      type="button"
      onClick={abrir}
      disabled={!habilitado}
      aria-haspopup="dialog"
      aria-expanded={abierto}
      className="fixed right-4 bottom-[5.75rem] z-30 grid size-14 place-items-center rounded-full bg-primary font-semibold text-primary-foreground shadow-[0_10px_24px_rgb(0_0_0/0.4)] transition-[background-color,box-shadow,translate] duration-150 enabled:hover:-translate-y-0.5 enabled:hover:bg-primary/80 enabled:hover:shadow-[0_14px_30px_rgb(0_0_0/0.5)] enabled:active:translate-y-px enabled:active:shadow-[0_6px_16px_rgb(0_0_0/0.4)] motion-reduce:transition-[background-color,box-shadow] motion-reduce:enabled:hover:translate-y-0 motion-reduce:enabled:active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50 md:right-8 md:bottom-8 md:inline-flex md:w-auto md:gap-2.5 md:pr-[1.375rem] md:pl-[1.125rem]"
    >
      <MessageCircle aria-hidden="true" className="size-6" />
      <span className="sr-only md:not-sr-only">{tf("askFilmAI")}</span>
      {noLeido && (
        <>
          <span
            aria-hidden="true"
            className="absolute top-0 right-0 size-3.5 rounded-full bg-destructive ring-2 ring-background"
          />
          <span className="sr-only">{t("unread")}</span>
        </>
      )}
    </button>
  );
}
