"use client";

import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { useAccount } from "@/components/AccountProvider";
import { routes } from "@/lib/routes";

/**
 * Enlace de regreso de Terms en celular (canvas «Terms · mobile»): con sesión
 * vuelve a Settings; sin sesión, a la portada. En escritorio lo reemplaza el
 * enlace de la página, por eso este componente no se muestra desde `md`.
 */
export function TermsBackLink() {
  const { perfil, cargando } = useAccount();
  const t = useTranslations("nav.main");
  // Mientras se resuelve la cuenta se reserva la altura para que el título no salte.
  if (cargando) return <div aria-hidden="true" className="h-11 md:hidden" />;
  return (
    <Link
      href={perfil ? routes.settings : routes.home}
      className="-ml-2.5 inline-flex h-11 items-center gap-1 self-start px-2.5 text-[15px] font-medium text-fg-2 md:hidden"
    >
      <ChevronLeft aria-hidden="true" className="size-4" />
      {perfil ? t("settings") : t("backLanding")}
    </Link>
  );
}
