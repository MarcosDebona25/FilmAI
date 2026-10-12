"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { AccountMenu } from "@/components/AccountMenu";
import { useAccount } from "@/components/AccountProvider";
import { TicketMark } from "@/components/access/Logo";
import { isAccessPath, routes } from "@/lib/routes";

const NAV_LINKS = [
  { key: "home", href: routes.explore },
  { key: "search", href: routes.search },
  { key: "lists", href: routes.lists },
] as const;

const authLinkClass =
  "inline-flex h-11 items-center rounded-[10px] px-4 text-[15px] font-semibold no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

/** Encabezado del sitio: marca, navegación principal (escritorio) y cuenta. */
export function Navbar() {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const { perfil, cargando } = useAccount();

  if (isAccessPath(pathname)) return null;

  return (
    <header>
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-card focus:p-3 focus:text-foreground focus:outline-2 focus:outline-ring"
      >
        {t("main.skipToContent")}
      </a>
      <div className="mx-auto flex h-[60px] max-w-[1360px] items-center gap-10 pr-3 pl-5 md:h-auto md:px-10 md:py-5">
        <Link
          href={routes.explore}
          aria-label={t("main.brandHomeLabel")}
          className="flex items-center gap-2 text-foreground no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:gap-2.5"
        >
          <TicketMark width={28} height={21} className="md:h-6 md:w-8" />
          <span
            translate="no"
            className="font-display text-[26px] leading-none tracking-[0.05em] md:text-[30px]"
          >
            FilmAI
          </span>
        </Link>
        <nav aria-label={t("main.mainLabel")} className="hidden gap-1 md:flex">
          {NAV_LINKS.map((item) => {
            const current = pathname === item.href;
            return (
              <Link
                key={item.key}
                href={item.href}
                aria-current={current ? "page" : undefined}
                className={`flex h-11 items-center rounded-lg px-3 text-[15px] font-medium no-underline hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring ${current ? "text-foreground" : "text-fg-2"}`}
              >
                {t(`main.${item.key}`)}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {cargando ? null : perfil ? (
            <AccountMenu />
          ) : (
            <>
              <Link href={routes.login} className={`${authLinkClass} text-foreground`}>
                {t("account.logIn")}
              </Link>
              <Link
                href={routes.register}
                className={`${authLinkClass} bg-primary text-primary-foreground hover:brightness-95`}
              >
                {t("account.signUp")}
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
