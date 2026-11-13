import { useTranslations } from "next-intl";

/**
 * Créditos de TMDB (canvas «Terms · desktop/mobile»): título, logo oficial como
 * enlace al sitio y el aviso exacto que exige TMDB. Cierra `/terms` y el pie
 * enlaza acá con `#credits`.
 *
 * El logo es un `<img>` del archivo oficial en `public/tmdb/`, sin tocar:
 * ni filtros ni `currentColor`, que lo recolorearían. Solo la altura está
 * fija; `w-auto` mantiene la proporción original.
 */
export function TmdbCredits() {
  const t = useTranslations("tmdb.credits");
  return (
    <section
      id="credits"
      aria-labelledby="credits-title"
      className="flex scroll-mt-24 flex-col gap-3 border-t border-border py-7 md:py-8"
    >
      <h2
        id="credits-title"
        className="font-display text-[1.75rem] leading-[1.05] md:text-[1.875rem]"
      >
        {t("title")}
      </h2>
      <a
        href="https://www.themoviedb.org"
        rel="noopener"
        className="inline-flex self-start focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- archivo oficial sin tocar */}
        <img
          src="/tmdb/logo5.svg"
          alt={t("logoAlt")}
          className="block h-[1.125rem] w-auto md:h-5"
        />
      </a>
      <p className="max-w-[68ch] leading-[1.7] text-muted-foreground">{t("notice")}</p>
    </section>
  );
}
