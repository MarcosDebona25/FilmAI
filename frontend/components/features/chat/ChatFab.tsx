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
  const pathname = usePathname();
  const { habilitado, abierto, abrir, fabRef } = useChat();
  if (isAccessPath(pathname)) return null;
  return (
    <button
      ref={fabRef}
      type="button"
      onClick={abrir}
      disabled={!habilitado}
      aria-haspopup="dialog"
      aria-expanded={abierto}
      className="fixed right-4 bottom-[5.75rem] z-30 grid size-14 place-items-center rounded-full bg-primary font-semibold text-primary-foreground shadow-[0_10px_24px_rgb(0_0_0/0.4)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-50 md:right-8 md:bottom-8 md:inline-flex md:w-auto md:gap-2.5 md:pr-[1.375rem] md:pl-[1.125rem]"
    >
      <MessageCircle aria-hidden="true" className="size-6" />
      <span className="sr-only md:not-sr-only">{tf("askFilmAI")}</span>
    </button>
  );
}
