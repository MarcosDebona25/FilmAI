"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { AccountMenu } from "@/components/AccountMenu";
import { useAccount } from "@/components/AccountProvider";
import { TicketMark } from "@/components/access/Logo";
import { isAccessPath, routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { key: "home", href: routes.explore },
  { key: "search", href: routes.search },
  { key: "lists", href: routes.lists },
] as const;

const authLinkClass =
  "inline-flex h-11 items-center rounded-[0.625rem] px-3 text-[0.9375rem] font-semibold md:px-4 no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";

type Fondo = "transparente" | "translucido" | "solido";

const CLASES_FONDO: Record<Fondo, string | undefined> = {
  transparente: undefined,
  // Con la imagen debajo: el título o el póster que pasan no tapan los enlaces.
  translucido: "md:bg-background/85 md:backdrop-blur-lg",
  solido: "md:bg-background md:shadow-[inset_0_-1px_0_var(--line)]",
};

/**
 * Fondo de la barra según el scroll: nada con la página arriba de todo,
 * translúcido mientras tiene debajo la imagen grande de la página
 * (`data-imagen-bajo-navbar`) y sólido después, o si no hay imagen.
 */
function useFondo(barra: React.RefObject<HTMLElement | null>, pathname: string) {
  const [fondo, setFondo] = useState<Fondo>("transparente");

  useEffect(() => {
    const actualizar = () => {
      const imagen = document.querySelector("[data-imagen-bajo-navbar]");
      const alto = barra.current?.offsetHeight ?? 0;
      if (window.scrollY <= 0) setFondo("transparente");
      else if (imagen && imagen.getBoundingClientRect().bottom > alto) setFondo("translucido");
      else setFondo("solido");
    };
    actualizar();
    window.addEventListener("scroll", actualizar, { passive: true });
    window.addEventListener("resize", actualizar);
    return () => {
      window.removeEventListener("scroll", actualizar);
      window.removeEventListener("resize", actualizar);
    };
  }, [barra, pathname]);

  return fondo;
}

/** Encabezado del sitio: marca, navegación principal (escritorio) y cuenta. */
export function Navbar() {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const { perfil, cargando } = useAccount();
  const barra = useRef<HTMLElement>(null);
  const fondo = useFondo(barra, pathname);

  if (isAccessPath(pathname)) return null;

  const posicion =
    pathname === routes.explore
      ? "md:fixed md:inset-x-0"
      : /^\/(movie|tv)\/\d+$/.test(pathname)
        ? "absolute inset-x-0 z-20 md:fixed"
        : "md:sticky";

  return (
    // En escritorio queda siempre visible (04/11/2026). Sobre la imagen de fondo
    // (canvas) no ocupa lugar: en el Home solo en escritorio (C-05); en la ficha,
    // siempre (C-07). En celular se va con la página: abajo está MobileTabs.
    <header
      ref={barra}
      className={cn(posicion, "top-0 md:z-30 md:transition-colors", CLASES_FONDO[fondo])}
    >
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-card focus:p-3 focus:text-foreground focus:outline-2 focus:outline-ring"
      >
        {t("main.skipToContent")}
      </a>
      <div className="page-container max-md:pr-3 flex h-[3.75rem] items-center gap-4 md:gap-10 md:h-auto md:py-5">
        <Link
          href={routes.explore}
          aria-label={t("main.brandHomeLabel")}
          className="flex items-center gap-2 text-foreground no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:gap-2.5"
        >
          <TicketMark width={28} height={21} className="md:h-6 md:w-8" />
          <span
            translate="no"
            className="font-display text-[1.625rem] leading-none tracking-[0.05em] md:text-[1.875rem]"
          >
            FilmAI
          </span>
        </Link>
        <nav aria-label={t("main.mainLabel")} className="hidden gap-1 md:flex">
          {NAV_LINKS.filter((item) => item.key !== "lists" || perfil).map((item) => {
            const current = pathname === item.href;
            return (
              <Link
                key={item.key}
                href={item.href}
                aria-current={current ? "page" : undefined}
                className={`flex h-11 items-center rounded-lg px-3 text-[0.9375rem] font-medium no-underline hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring ${current ? "text-foreground" : "text-fg-2"}`}
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
              {/* En celular, Log in vive en la barra inferior (MobileTabs). */}
              <Link
                href={routes.login}
                className={`${authLinkClass} text-foreground max-md:hidden`}
              >
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
