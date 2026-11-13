"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Globe } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { useAccount } from "@/components/AccountProvider";
import { useChat } from "@/components/ChatProvider";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { TicketMark } from "@/components/access/Logo";
import { isAccessPath, routes } from "@/lib/routes";

const linkClass =
  "inline-flex min-h-8 items-center gap-2 text-sm text-fg-2 no-underline hover:text-foreground hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";
const rowClass =
  "flex min-h-12 items-center justify-between text-[0.9375rem] font-medium text-fg-2 no-underline hover:text-foreground focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring";

/**
 * «Ask FilmAI» del pie: con sesión abre el panel del chat; sin sesión lleva al
 * login y vuelve a la página actual (el FAB, en cambio, se ve deshabilitado).
 */
function AskFilmAI({ className, children }: { className: string; children: React.ReactNode }) {
  const { habilitado, abrir } = useChat();
  const pathname = usePathname();
  if (habilitado) {
    return (
      <button type="button" onClick={abrir} aria-haspopup="dialog" className={className}>
        {children}
      </button>
    );
  }
  return (
    <Link href={`${routes.login}?next=${encodeURIComponent(pathname)}`} className={className}>
      {children}
    </Link>
  );
}

/** Pie del sitio (canvas «Footer»): columnas en escritorio, lista de filas en celular. */
export function Footer() {
  const { perfil, cargando } = useAccount();
  const pathname = usePathname();
  const locale = useLocale();
  const t = useTranslations("footer.main");
  const nav = useTranslations("nav.main");
  const account = useTranslations("nav.account");
  const common = useTranslations("common.actions");
  const language = useTranslations("settings.language");
  const credits = useTranslations("tmdb.credits");

  if (cargando || isAccessPath(pathname)) return null;

  const languageName = language(locale === "en" ? "english" : "spanish");
  const languageLabel = t("languageLink", { language: languageName });
  const headingClass = "m-0 text-[0.8125rem] font-bold uppercase tracking-[0.08em] text-fg-3";
  const year = String(new Date().getFullYear());

  return (
    <footer className="mt-10 border-t border-line">
      <div className="page-container flex flex-col gap-6 pt-9 pb-5 md:gap-12 md:pt-14 md:pb-10">
        <div className="flex flex-wrap justify-between gap-x-16 gap-y-10">
          <div className="flex max-w-[31.5625rem] flex-1 basis-80 flex-col gap-3 md:gap-4">
            <Link
              href={routes.explore}
              aria-label={nav("brandHomeLabel")}
              className="inline-flex items-center gap-2 text-foreground no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:gap-2.5"
            >
              <TicketMark width={28} height={21} className="md:h-6 md:w-8" />
              <span
                translate="no"
                className="font-display text-[1.625rem] leading-none tracking-[0.05em] md:text-[1.875rem]"
              >
                FilmAI
              </span>
            </Link>
            <p className="m-0 hidden text-[0.9375rem] text-fg-2 md:block">
              {t("descriptionDesktop")}
            </p>
            <p className="m-0 text-sm text-fg-2 md:hidden">{t("descriptionMobile")}</p>
          </div>

          <div className="hidden flex-wrap gap-x-[4.5rem] gap-y-10 md:flex">
            <nav aria-label={common("explore")} className="flex flex-col gap-3">
              <h2 className={headingClass}>{common("explore")}</h2>
              <ul className="m-0 flex list-none flex-col gap-0.5 p-0">
                <li>
                  <Link href={routes.explore} className={linkClass}>
                    {nav("home")}
                  </Link>
                </li>
                <li>
                  <Link href={routes.search} className={linkClass}>
                    {nav("search")}
                  </Link>
                </li>
                <li>
                  <AskFilmAI className={linkClass}>{t("askFilmAI")}</AskFilmAI>
                </li>
              </ul>
            </nav>
            <nav aria-label={t("libraryHeading")} className="flex flex-col gap-3">
              <h2 className={headingClass}>{t("libraryHeading")}</h2>
              <ul className="m-0 flex list-none flex-col gap-0.5 p-0">
                <li>
                  <Link href={routes.lists} className={linkClass}>
                    {t("myLists")}
                  </Link>
                </li>
                <li>
                  <Link href={routes.myReviews} className={linkClass}>
                    {nav("ratingsReviews")}
                  </Link>
                </li>
                <li>
                  <Link href={routes.profile} className={linkClass}>
                    {nav("profile")}
                  </Link>
                </li>
                <li>
                  <Link href={routes.settings} className={linkClass}>
                    {nav("settings")}
                  </Link>
                </li>
              </ul>
            </nav>
            <nav aria-label={t("informationHeading")} className="flex flex-col gap-3">
              <h2 className={headingClass}>{t("informationHeading")}</h2>
              <ul className="m-0 flex list-none flex-col gap-0.5 p-0">
                <li>
                  <Link href={routes.terms} className={linkClass}>
                    {nav("terms")}
                  </Link>
                </li>
                {perfil ? (
                  <li>
                    <Link href={routes.language} aria-label={languageLabel} className={linkClass}>
                      <Globe aria-hidden="true" className="size-[0.9375rem] flex-none" />
                      <span lang={locale}>{languageName}</span>
                    </Link>
                  </li>
                ) : (
                  <>
                    <li>
                      <Link href={routes.register} className={linkClass}>
                        {account("signUp")}
                      </Link>
                    </li>
                    <li>
                      <Link href={routes.login} className={linkClass}>
                        {account("logIn")}
                      </Link>
                    </li>
                    <li className="pt-1.5">
                      <LanguageSwitcher />
                    </li>
                  </>
                )}
              </ul>
            </nav>
          </div>
        </div>

        <ul className="m-0 flex list-none flex-col border-t border-line p-0 md:hidden">
          <li className="border-b border-line">
            <Link href={routes.terms} className={rowClass}>
              {nav("terms")}
              <ChevronRight aria-hidden="true" className="size-4" />
            </Link>
          </li>
          <li className="border-b border-line">
            <AskFilmAI className={`${rowClass} w-full`}>
              {t("askFilmAI")}
              <ChevronRight aria-hidden="true" className="size-4" />
            </AskFilmAI>
          </li>
          {perfil ? (
            <li className="border-b border-line">
              <Link href={routes.language} aria-label={languageLabel} className={rowClass}>
                <span className="inline-flex items-center gap-2.5">
                  <Globe aria-hidden="true" className="size-4 flex-none" />
                  {language("label")}
                </span>
                <span className="inline-flex items-center gap-1.5 font-normal text-fg-3">
                  <span lang={locale}>{languageName}</span>
                  <ChevronRight aria-hidden="true" className="size-4" />
                </span>
              </Link>
            </li>
          ) : (
            <>
              <li className="border-b border-line">
                <Link href={routes.register} className={rowClass}>
                  {account("signUp")}
                  <ChevronRight aria-hidden="true" className="size-4" />
                </Link>
              </li>
              {/* Log in no va acá: en celular está en la barra inferior. */}
              <li className="py-3">
                <LanguageSwitcher />
              </li>
            </>
          )}
        </ul>

        <div className="flex flex-col gap-2 text-xs text-fg-3 md:flex-row md:flex-wrap md:items-center md:justify-between md:gap-x-8 md:gap-y-3 md:border-t md:border-line md:pt-7 md:text-[0.8125rem]">
          <div className="flex flex-col gap-2.5 md:max-w-[47.5rem]">
            <a
              href="https://www.themoviedb.org"
              rel="noopener"
              className="inline-flex self-start focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- archivo oficial sin tocar */}
              <img src="/tmdb/logo5.svg" alt={credits("logoAlt")} className="block h-4 w-auto" />
            </a>
            <p className="m-0">
              {t("tmdbAttribution")}{" "}
              <Link
                href={`${routes.terms}#credits`}
                className="text-fg-2 underline underline-offset-[3px] hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                {t("creditsLink")}
              </Link>
            </p>
          </div>
          <p className="m-0">{t("copyright", { year })}</p>
        </div>
      </div>
    </footer>
  );
}
