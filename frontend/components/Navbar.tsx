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

// El mismo corte que `md:` de Tailwind: los fondos solo existen en escritorio.
const ESCRITORIO = "(width >= 48rem)";

/** Si la pantalla es de escritorio, y se actualiza si cambia el ancho. */
function useEscritorio() {
  const [escritorio, setEscritorio] = useState(false);
  useEffect(() => {
    // `?.`: en los tests (jsdom) `matchMedia` puede no existir.
    const consulta = window.matchMedia?.(ESCRITORIO);
    if (!consulta) return;
    const leer = () => setEscritorio(consulta.matches);
    leer();
    consulta.addEventListener?.("change", leer);
    return () => consulta.removeEventListener?.("change", leer);
  }, []);
  return escritorio;
}

/**
 * Fondo de la barra según el scroll: nada con la página arriba de todo,
 * translúcido mientras tiene debajo la imagen grande de la página
 * (`data-imagen-bajo-navbar`) y sólido después, o si no hay imagen.
 *
 * Quién avisa cada cosa:
 * - si la página está arriba de todo, el evento `scroll`, que solo lee
 *   `window.scrollY` (barato: no obliga al navegador a medir nada);
 * - si la imagen sigue debajo de la barra, un `IntersectionObserver`. El
 *   navegador avisa solo cuando eso cambia, también si la imagen cambia de
 *   alto sin que nadie haga scroll (el hero del Inicio al terminar de cargar).
 *
 * En celular no hace nada: las clases de fondo son solo `md:`.
 */
export function useFondo(barra: React.RefObject<HTMLElement | null>, pathname: string) {
  const [fondo, setFondo] = useState<Fondo>("transparente");
  const escritorio = useEscritorio();

  useEffect(() => {
    if (!escritorio) {
      setFondo("transparente");
      return;
    }
    const imagen = document.querySelector("[data-imagen-bajo-navbar]");
    const alto = barra.current?.offsetHeight ?? 0;
    // Variables comunes, no estado de React: cambian muy seguido y solo
    // importan para elegir el fondo. Lo que se renderiza es `fondo`.
    let arriba = window.scrollY <= 0;
    // Una sola medición al empezar; después avisa el observador.
    let imagenDebajo = imagen ? imagen.getBoundingClientRect().bottom > alto : false;

    const decidir = () =>
      setFondo(arriba ? "transparente" : imagenDebajo ? "translucido" : "solido");
    const alScroll = () => {
      const ahora = window.scrollY <= 0;
      if (ahora !== arriba) {
        arriba = ahora;
        decidir();
      }
    };

    let observador: IntersectionObserver | undefined;
    if (imagen) {
      // El margen negativo arriba achica la zona observada en el alto de la
      // barra: la imagen cuenta como visible solo si asoma por debajo de ella.
      observador = new IntersectionObserver(
        ([entrada]) => {
          imagenDebajo = entrada.isIntersecting;
          decidir();
        },
        { rootMargin: `-${alto}px 0px 0px 0px` }
      );
      observador.observe(imagen);
    }
    decidir();
    window.addEventListener("scroll", alScroll, { passive: true });
    return () => {
      observador?.disconnect();
      window.removeEventListener("scroll", alScroll);
    };
  }, [barra, pathname, escritorio]);

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
    // `data-navbar`: globals.css reserva espacio arriba (scroll-padding-top) solo
    // en las páginas que tienen esta barra.
    <header
      ref={barra}
      data-navbar=""
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
