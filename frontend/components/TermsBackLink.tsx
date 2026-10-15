"use client";

import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { useAccount } from "@/components/AccountProvider";
import { TicketMark } from "@/components/access/Logo";
import { routes } from "@/lib/routes";

/**
 * Regreso de Terms según haya sesión (canvas «Terms»). En celular, un enlace:
 * a Settings con sesión, a la portada sin ella. En escritorio, con sesión, la
 * miga Profile › Settings › Terms; sin sesión, «Back to the landing page».
 */
export function TermsBackLink() {
  const { perfil, cargando } = useAccount();
  const t = useTranslations("nav.main");
  // Mientras se resuelve la cuenta se reserva la altura para que el título no salte.
  if (cargando) return <div aria-hidden="true" className="h-11" />;
  return (
    <>
      <Link
        href={perfil ? routes.settings : routes.home}
        className="-ml-2.5 inline-flex h-11 items-center gap-1 self-start px-2.5 text-[15px] font-medium text-fg-2 md:hidden"
      >
        <ChevronLeft aria-hidden="true" className="size-4" />
        {perfil ? t("settings") : t("backLanding")}
      </Link>
      {perfil ? (
        <nav aria-label={t("breadcrumbLabel")} className="hidden text-sm text-fg-2 md:block">
          <ol className="flex flex-wrap items-center gap-2">
            <li>
              <Link href={routes.profile} className="text-fg-2 hover:text-foreground">
                {t("profileShort")}
              </Link>
            </li>
            <li aria-hidden="true">›</li>
            <li>
              <Link href={routes.settings} className="text-fg-2 hover:text-foreground">
                {t("settings")}
              </Link>
            </li>
            <li aria-hidden="true">›</li>
            <li aria-current="page" className="font-semibold text-foreground">
              {t("terms")}
            </li>
          </ol>
        </nav>
      ) : (
        <Link
          href={routes.home}
          className="hidden min-h-11 items-center gap-2 self-start text-sm font-semibold text-muted-foreground md:inline-flex"
        >
          <TicketMark width={24} height={18} />
          {t("backLanding")}
        </Link>
      )}
    </>
  );
}
