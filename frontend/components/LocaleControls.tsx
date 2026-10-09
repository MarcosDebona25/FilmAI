"use client";
import Link from "next/link";
import { Globe, ChevronRight } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname } from "next/navigation";
import { useAccount } from "./AccountProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { routes } from "@/lib/routes";

export function PublicLanguageControl() {
  const path = usePathname();
  const { perfil, cargando } = useAccount();
  if (
    perfil ||
    cargando ||
    !([routes.home, routes.login, routes.register] as readonly string[]).includes(path)
  )
    return null;
  return (
    <div className="absolute top-4 right-4 z-20">
      <LanguageSwitcher compact />
    </div>
  );
}

export function Footer() {
  const { perfil, cargando } = useAccount();
  const locale = useLocale();
  const language = useTranslations("settings.language");
  const t = useTranslations("footer.main");
  const nav = useTranslations("nav.main");
  const auth = useTranslations("nav.account");
  if (cargando) return null;
  const languageLink = (
    <Link
      href={routes.language}
      className="flex min-h-11 items-center gap-2 rounded-md px-2 text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
    >
      <Globe aria-hidden="true" className="size-4" />
      {language("label")} ·{" "}
      <span lang={locale}>{language(locale === "en" ? "english" : "spanish")}</span>
      <ChevronRight aria-hidden="true" className="ml-auto size-4" />
    </Link>
  );
  return (
    <footer className="mt-10 border-t border-border bg-card px-6 py-8">
      <div className="mx-auto max-w-5xl">
        <div className="hidden items-start justify-between gap-8 md:flex">
          <Link
            href={routes.home}
            className="min-h-11 text-xl font-bold focus-visible:outline-2 focus-visible:outline-ring"
            translate="no"
          >
            FilmAI
          </Link>
          {perfil ? (
            <nav aria-label={t("libraryHeading")} className="grid gap-2">
              <Link className="min-h-11 hover:underline" href={routes.profile}>
                {nav("profile")}
              </Link>
              <Link className="min-h-11 hover:underline" href={routes.myReviews}>
                {nav("ratingsReviews")}
              </Link>
            </nav>
          ) : (
            <nav aria-label={t("libraryHeading")} className="grid gap-2">
              <Link className="min-h-11 hover:underline" href={routes.register}>
                {auth("signUp")}
              </Link>
              <Link className="min-h-11 hover:underline" href={routes.login}>
                {auth("logIn")}
              </Link>
            </nav>
          )}
          <section aria-label={t("informationHeading")}>
            <h2 className="mb-3 font-semibold">{t("informationHeading")}</h2>
            {perfil ? languageLink : <LanguageSwitcher />}
          </section>
        </div>
        {perfil && <div className="md:hidden">{languageLink}</div>}
        <p className="mt-6 text-xs text-foreground/75">
          {t("copyright", { year: String(new Date().getFullYear()) })}
        </p>
      </div>
    </footer>
  );
}
